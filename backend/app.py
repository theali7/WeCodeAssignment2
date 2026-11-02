"""Local account API implementing only the Supabase client calls used by WeCode.

This is not a general GoTrue or PostgREST implementation.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time
from uuid import uuid4, UUID
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from . import db
from .security import access_token, verify_access, password_hash, password_matches, token_hash

TABLES = {
    "profiles": ("id", "display_name", "path_id", "level"),
    "lessons": ("id", "path_id", "slug", "title_en", "content_en", "title_ru", "content_ru", "position", "published"),
    "lesson_progress": ("user_id", "lesson_id", "completed", "updated_at"),
    "learning_way_progress": ("user_id", "item_id", "created_at"),
}
KEYS = {"profiles": ("id",), "lesson_progress": ("user_id", "lesson_id"),
        "learning_way_progress": ("user_id", "item_id")}
STATIC = Path(os.environ.get("STATIC_DIRECTORY", "/app/static"))
_attempts = {}
_attempt_lock = threading.Lock()


def error(status, message, code="request_error"):
    raise HTTPException(status, detail={"message": message, "error_code": code, "code": code})


def secret():
    value = os.environ.get("AUTH_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("AUTH_SECRET must contain at least 32 characters")
    return value


def public_origin():
    """Use an operator-set HTTPS origin; never trust client forwarding headers."""
    value = os.environ.get("PUBLIC_ORIGIN") or os.environ.get("RENDER_EXTERNAL_URL") or ""
    if not value:
        return None
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None
        or parsed.password is not None or parsed.path not in ("", "/")
        or parsed.query or parsed.fragment or any(c.isspace() for c in value)):
        raise ValueError("PUBLIC_ORIGIN/RENDER_EXTERNAL_URL must be one HTTPS origin")
    parsed.port
    return "https://" + parsed.netloc


def rate_limit(request):
    # Bound credential hashing on the single-process assignment server.
    address = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _attempt_lock:
        for key in list(_attempts):
            if now - _attempts[key][0] >= 60:
                del _attempts[key]
        start, count = _attempts.get(address, (now, 0))
        if count >= 30 or len(_attempts) > 10000:
            error(429, "Too many attempts. Try again in a minute.", "over_request_rate_limit")
        _attempts[address] = (start, count + 1)


def public_user(row):
    return {"id": str(row["id"]), "email": row["email"], "aud": "authenticated",
        "role": "authenticated", "app_metadata": {"provider": "email", "providers": ["email"]},
        "user_metadata": {"display_name": row["display_name"]},
        "created_at": row["created_at"].isoformat(), "email_confirmed_at": row["created_at"].isoformat(),
        "identities": []}


def session_response(connection, user, session_id=None):
    refresh = secrets.token_urlsafe(48)
    session_id = session_id or uuid4()
    connection.execute("INSERT INTO wecode_private.sessions(id,user_id,refresh_hash,expires_at) VALUES(%s,%s,%s,%s) "
        "ON CONFLICT(id) DO UPDATE SET refresh_hash=excluded.refresh_hash,expires_at=excluded.expires_at",
        (session_id, user["id"], token_hash(refresh), datetime.now(timezone.utc) + timedelta(days=7)))
    return {"access_token": access_token(user["id"], session_id, secret()), "refresh_token": refresh,
        "expires_in": 3600, "expires_at": int(time.time()) + 3600,
        "token_type": "bearer", "user": public_user(user)}


def identity(request, connection):
    try:
        value = request.headers.get("authorization", "")
        if not value.lower().startswith("bearer "):
            raise ValueError()
        claims = verify_access(value[7:], secret())
        user_id, session_id = UUID(claims["sub"]), UUID(claims["sid"])
    except ValueError:
        error(401, "Please sign in again.", "bad_jwt")
    user = connection.execute("SELECT u.* FROM wecode_private.users u JOIN wecode_private.sessions s ON s.user_id=u.id "
        "WHERE u.id=%s AND s.id=%s AND s.expires_at>now()", (user_id, session_id)).fetchone()
    if not user:
        error(401, "Session expired. Please sign in again.", "session_not_found")
    return user, session_id


@asynccontextmanager
async def lifespan(app):
    secret()
    public_origin()
    db.migrate_with_retry()
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def limits_and_headers(request, call_next):
    length = request.headers.get("content-length", "0")
    if not length.isdigit() or int(length) > 65536:
        return JSONResponse({"message": "Request too large"}, status_code=413)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        # Same-origin browser writes only. API/CI clients without Origin still need authentication.
        origin = request.headers.get("origin")
        expected_origin = public_origin() or str(request.base_url).rstrip("/")
        if origin and origin != expected_origin:
            return JSONResponse({"message": "Cross-origin write rejected"}, status_code=403)
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "connect-src 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse(exc.detail if isinstance(exc.detail, dict) else {"message": exc.detail}, status_code=exc.status_code)


@app.get("/healthz")
def health():
    return Response("ok\n", media_type="text/plain")


@app.get("/api/health")
def ready():
    try:
        with db.connect() as connection:
            connection.execute("SELECT 1 FROM wecode_migrations LIMIT 1").fetchone()
        return {"status": "ok", "database": "postgresql"}
    except Exception:
        return JSONResponse({"status": "unavailable"}, status_code=503)


@app.get("/api/auth/v1/settings")
def settings():
    return {"external": {"email": True, "google": False, "github": False},
        "disable_signup": False, "mailer_autoconfirm": True, "phone_autoconfirm": False}


@app.post("/api/auth/v1/signup")
def signup(body: dict, request: Request):
    rate_limit(request)
    email = str(body.get("email", "")).strip().lower()
    password = body.get("password", "")
    data = body.get("data") or {}
    if not isinstance(data, dict):
        error(422, "Invalid profile data")
    name = str(data.get("display_name", "")).strip()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        error(422, "Enter a valid email address")
    if not isinstance(password, str) or not 8 <= len(password) <= 256 or len(name) > 80:
        error(422, "Password must be 8–256 characters; name must be at most 80 characters")
    hashed = password_hash(password)
    import psycopg
    try:
        with db.connect() as connection:
            user = connection.execute("INSERT INTO wecode_private.users(id,email,password_hash,display_name) "
                "VALUES(%s,%s,%s,%s) RETURNING *", (uuid4(), email, hashed, name)).fetchone()
            connection.execute("INSERT INTO profiles(id,display_name) VALUES(%s,%s)", (user["id"], name))
            return session_response(connection, user)
    except psycopg.errors.UniqueViolation:
        error(422, "An account with this email already exists", "user_already_exists")


@app.post("/api/auth/v1/token")
def login(body: dict, request: Request):
    rate_limit(request)
    with db.connect() as connection:
        grant = request.query_params.get("grant_type")
        if grant == "password":
            email = str(body.get("email", "")).strip().lower()
            password = body.get("password", "")
            if not isinstance(password, str) or len(password) > 256:
                error(400, "Invalid email or password", "invalid_credentials")
            user = connection.execute("SELECT * FROM wecode_private.users WHERE email=%s", (email,)).fetchone()
            if not user:
                password_hash(password)  # Avoid a fast missing-account path.
            if not user or not password_matches(password, user["password_hash"]):
                error(400, "Invalid email or password", "invalid_credentials")
            return session_response(connection, user)
        if grant == "refresh_token":
            refresh = body.get("refresh_token", "")
            if not isinstance(refresh, str) or len(refresh) > 256:
                error(400, "Invalid refresh token")
            session = connection.execute("SELECT * FROM wecode_private.sessions WHERE refresh_hash=%s AND expires_at>now() FOR UPDATE",
                (token_hash(refresh),)).fetchone()
            if not session:
                error(400, "Refresh token expired", "refresh_token_not_found")
            user = connection.execute("SELECT * FROM wecode_private.users WHERE id=%s", (session["user_id"],)).fetchone()
            return session_response(connection, user, session["id"])
        error(400, "Unsupported grant type")


@app.get("/api/auth/v1/user")
def get_user(request: Request):
    with db.connect() as connection:
        user, _ = identity(request, connection)
        return public_user(user)


@app.post("/api/auth/v1/logout")
def logout(request: Request):
    with db.connect() as connection:
        user, session_id = identity(request, connection)
        if request.query_params.get("scope", "global") == "local":
            connection.execute("DELETE FROM wecode_private.sessions WHERE id=%s", (session_id,))
        else:
            connection.execute("DELETE FROM wecode_private.sessions WHERE user_id=%s", (user["id"],))
    return Response(status_code=204)


@app.post("/api/auth/v1/recover")
def recover():
    error(501, "Password recovery is not configured for local accounts yet", "feature_not_configured")


@app.get("/api/rest/v1/{table}")
def read_table(table: str, request: Request):
    if table not in TABLES:
        error(404, "Unknown resource")
    allowed = TABLES[table]
    selected = request.query_params.get("select", "*").split(",")
    if selected == ["*"]:
        selected = list(allowed)
    if any(col not in allowed for col in selected):
        error(400, "Unknown column")
    with db.connect() as connection:
        user, _ = identity(request, connection)
        clauses, values = [], []
        if table == "lessons":
            clauses.append("published=true")
        else:
            owner = "id" if table == "profiles" else "user_id"
            clauses.append(f'"{owner}"=%s')
            values.append(user["id"])
        for key, value in request.query_params.multi_items():
            if key in ("select", "order", "limit", "offset"):
                continue
            if key not in allowed:
                error(400, "Unknown filter")
            if value.startswith("eq."):
                item = value[3:]
                if key in ("published", "completed"):
                    if item not in ("true", "false"):
                        error(400, "Invalid boolean")
                    item = item == "true"
                clauses.append(f'"{key}"=%s')
                values.append(item)
            elif value.startswith("in.(") and value.endswith(")"):
                items = value[4:-1].split(",")
                if len(items) > 100:
                    error(400, "Too many filter values")
                clauses.append(f'"{key}" IN (' + ",".join(["%s"] * len(items)) + ")")
                values.extend(items)
            else:
                error(400, "Unsupported filter")
        order = request.query_params.get("order", "")
        order_sql = ""
        if order:
            pieces = order.split(".")
            if pieces[0] not in allowed or pieces[1:] not in ([], ["asc"], ["desc"]):
                error(400, "Unsupported sort")
            order_sql = f' ORDER BY "{pieces[0]}" ' + ("DESC" if pieces[1:] == ["desc"] else "ASC")
        try:
            limit = min(max(int(request.query_params.get("limit", "1000")), 0), 1000)
            offset = max(int(request.query_params.get("offset", "0")), 0)
        except ValueError:
            error(400, "Invalid pagination")
        columns = ",".join('"' + col + '"' for col in selected)
        rows = connection.execute(f'SELECT {columns} FROM "{table}" WHERE ' + " AND ".join(clauses)
            + order_sql + " LIMIT %s OFFSET %s", (*values, limit, offset)).fetchall()
    if "application/vnd.pgrst.object" in request.headers.get("accept", ""):
        if len(rows) != 1:
            error(406, "JSON object requested, multiple (or no) rows returned", "PGRST116")
        return JSONResponse(jsonable_encoder(rows[0]))
    return JSONResponse(jsonable_encoder(rows))


@app.post("/api/rest/v1/{table}")
def write_table(table: str, body: list[dict] | dict, request: Request):
    if table not in KEYS:
        error(403, "Resource is read-only or unavailable")
    rows = body if isinstance(body, list) else [body]
    if not 1 <= len(rows) <= 100:
        error(400, "Expected 1–100 rows")
    keys = KEYS[table]
    conflict = request.query_params.get("on_conflict", ",".join(keys))
    if conflict.split(",") != list(keys):
        error(400, "Unsupported conflict key")
    import psycopg
    result = []
    try:
        with db.connect() as connection:
            user, _ = identity(request, connection)
            for row in rows:
                owner = "id" if table == "profiles" else "user_id"
                if str(row.get(owner, "")) != str(user["id"]):
                    error(403, "You can only update your own data")
                if any(col not in TABLES[table] or col == "created_at" for col in row):
                    error(400, "Unknown or read-only column")
                if any(key not in row for key in keys):
                    error(400, "Missing row key")
                if table == "profiles":
                    if ("level" in row and (type(row["level"]) is not int or not 0 <= row["level"] <= 2)
                            or "display_name" in row and (not isinstance(row["display_name"], str) or len(row["display_name"]) > 80)):
                        error(422, "Invalid profile values")
                if table == "learning_way_progress" and (not isinstance(row["item_id"], str) or not 1 <= len(row["item_id"]) <= 200):
                    error(422, "Invalid progress item")
                if table == "lesson_progress":
                    if "completed" in row and type(row["completed"]) is not bool:
                        error(422, "Invalid completion value")
                    if not connection.execute("SELECT 1 FROM lessons WHERE id=%s AND published", (row["lesson_id"],)).fetchone():
                        error(403, "Lesson unavailable")
                columns = list(row)
                quoted = ",".join('"' + c + '"' for c in columns)
                key_sql = ",".join('"' + c + '"' for c in keys)
                updates = [c for c in columns if c not in keys]
                action = "DO NOTHING"
                if updates and "resolution=ignore-duplicates" not in request.headers.get("prefer", ""):
                    action = "DO UPDATE SET " + ",".join(f'"{c}"=excluded."{c}"' for c in updates)
                saved = connection.execute(f'INSERT INTO "{table}" ({quoted}) VALUES (' + ",".join(["%s"] * len(columns))
                    + f') ON CONFLICT ({key_sql}) {action} RETURNING *', tuple(row[c] for c in columns)).fetchone()
                if saved:
                    result.append(saved)
    except (psycopg.errors.CheckViolation, psycopg.errors.InvalidTextRepresentation, psycopg.errors.NotNullViolation,
            psycopg.errors.ForeignKeyViolation, psycopg.errors.DatetimeFieldOverflow):
        error(422, "Invalid record values")
    if "return=representation" in request.headers.get("prefer", ""):
        return JSONResponse(jsonable_encoder(result), status_code=201)
    return Response(status_code=201)


if STATIC.exists():
    if (STATIC / "runtimes").is_dir():
        app.mount("/runtimes", StaticFiles(directory=STATIC / "runtimes"), name="runtimes")
    app.mount("/assets", StaticFiles(directory=STATIC / "assets"), name="assets")
    app.mount("/fonts", StaticFiles(directory=STATIC / "fonts"), name="fonts")
    app.mount("/tech", StaticFiles(directory=STATIC / "tech"), name="tech")

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")
