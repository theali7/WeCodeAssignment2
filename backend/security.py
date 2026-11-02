"""Password hashing and short-lived signed access tokens for local accounts."""
import base64
import hashlib
import hmac
import json
import secrets
import time


def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def unb64(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600_000)
    return f"pbkdf2_sha256$600000${salt}${digest.hex()}"


def password_matches(password, encoded):
    try:
        method, rounds, salt, digest = encoded.split("$")
        if method != "pbkdf2_sha256" or rounds != "600000":
            return False
        return hmac.compare_digest(password_hash(password, salt), encoded)
    except (ValueError, TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def access_token(user_id, session_id, secret, now=None):
    now = int(time.time()) if now is None else now
    header = b64(b'{"alg":"HS256","typ":"JWT"}')
    payload = b64(json.dumps({"sub": str(user_id), "sid": str(session_id),
        "aud": "authenticated", "role": "authenticated", "iss": "wecode-assignment",
        "iat": now, "exp": now + 3600}, separators=(",", ":")).encode())
    message = header + "." + payload
    return message + "." + b64(hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest())


def verify_access(token, secret, now=None):
    now = int(time.time()) if now is None else now
    try:
        header, payload, signature = token.split(".")
        expected = b64(hmac.new(secret.encode(), (header + "." + payload).encode(), hashlib.sha256).digest())
        claims = json.loads(unb64(payload))
        if (not hmac.compare_digest(signature, expected)
                or json.loads(unb64(header)) != {"alg": "HS256", "typ": "JWT"}
                or claims.get("iss") != "wecode-assignment"
                or claims.get("aud") != "authenticated"
                or claims.get("exp", 0) <= now
                or not isinstance(claims.get("sub"), str)
                or not isinstance(claims.get("sid"), str)):
            raise ValueError("Invalid access token")
        return claims
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        raise ValueError("Invalid access token") from exc
