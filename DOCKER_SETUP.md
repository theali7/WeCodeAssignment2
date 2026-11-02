# Local backend and PostgreSQL

This assignment stack is isolated from the original hosted WeCode and production Supabase. Existing production accounts, passwords and records are not copied. Create a new local account.

## Start on macOS

Start Docker Desktop, then run:

```sh
cd ~/WeCodeAssignment2
git pull --ff-only
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
python3 scripts/setup_env.py
docker compose up --build -d
docker compose ps
curl -f http://localhost:8080/api/health
```

Open http://localhost:8080. Sign up with an email and a new password of at least 8 characters. Local accounts are immediately confirmed; no email is sent. Test sign-out, sign-in, learning preferences, and a Learning Way completion after reloading.

The `.env` generator creates random local database and authentication secrets once and does not overwrite existing values. Keep `.env` private. Do not change the database password after the volume is initialized without also changing it in PostgreSQL.

## Architecture

The single Dockerfile packages the recovered static frontend and a Python/FastAPI backend. Compose runs that application and PostgreSQL 17. PostgreSQL has no host port; the website binds only to 127.0.0.1:8080. Database records persist in the named assignment_postgres volume. Startup applies versioned migrations under an advisory lock and rejects modifications to applied migration files.

During image creation, scripts/prepare_frontend.py changes exactly one captured API URL to `window.location.origin + '/api'`. The original recovered bundle remains intact in Git. External browser connections remain blocked by CSP. The old Nginx preview is no longer used.

The backend implements the limited Supabase client contract actually used by the recovered interface: email signup/login, refresh-token rotation, session lookup, logout, profiles, published lessons, lesson_progress and learning_way_progress. It is not a general Supabase/PostgREST replacement. Every private read/write is scoped to the authenticated user by the backend. Database identifiers are allowlisted and values are bound as parameters. Passwords are salted PBKDF2 hashes; refresh tokens are stored as hashes. Logout revokes stored sessions, including their still-unexpired access tokens.

## Scope and limitations

- Google/GitHub OAuth and email password recovery are not configured locally. Recovery returns an explicit unsupported-feature error.
- Problems content and the built-in Learning Way course content remain in the recovered frontend. Problem submissions currently retain the frontend's existing storage behavior; this change does not introduce a server code-execution service or migrate all browser storage.
- The lessons table starts empty. No production lesson rows or user progress were extracted. Learning Way completion records can be saved in the new database.
- No SQLite database was found in the imported tracked project. This is an isolated PostgreSQL schema setup, not a claimed SQLite data migration. The original Supabase SQL depends on its auth schema and is not applied to this database.
- The saved Sites source was recovered at source commit 7bab7f837f32a537ad691e99af5b5c719f37205b. Runtime workers are imported here; the Docker UI still serves the identical captured frontend, and src/ still contains the older imported source. Migrating editable frontend source is separate. Five recovered Gilroy weights are included.
- This is a local assignment foundation. Render demonstration hosting and CI-gated redeployment are verified as described in README.md. AWS/GCP infrastructure, SMTP/OAuth and production hardening remain separate tasks. The credential-attempt limiter is per process; the image intentionally runs one worker.

## Validation

```sh
python -m unittest discover -s tests -v
```

Security/frontend-wiring and hosting unit tests run without a database. Seven integration tests require `WECODE_TEST_DATABASE_URL` pointing to a disposable test database. GitHub Actions provisions PostgreSQL and runs all tests plus a Docker build and Compose validation. Tests only remove the random accounts they create. CI is not a substitute for checking the actual browser signup/login/progress flow.

Inspect runtime problems with `docker compose logs --tail=100 web db`. Stop with `docker compose down`; this preserves the database volume. Do not use `down -v` unless you intend to delete all local assignment accounts and progress.

## Browser execution engines

The recovered Python, Java and SQL workers run on the visitor's device. During Docker build, scripts/prepare_runtimes.py downloads pinned Pyodide 0.29.3 and PGlite 0.5.13 npm distributions plus TeaVM playground/3 compiler assets. Every archive and selected file is SHA-256 checked against scripts/runtime-manifest.json; changed upstream bytes fail the build. Runtime assets are served from /runtimes on the application origin, so browsers need no external CDN or production credentials. The build needs upstream availability; the completed image does not. Restore the exact pinned bytes or deliberately review a version update if an upstream file changes.

These browser results are practice feedback; they are not a trusted server judge. SQL exercises run in a separate in-browser PostgreSQL instance, not the account database. Full-topic Playwright tests require five genuinely accepted submissions before checking persistence in a fresh browser context.
