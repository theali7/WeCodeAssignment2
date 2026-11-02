# Docker: initial static preview

Related issues: #2, #3, #4. This is an intermediate setup, not the completed full-stack assignment.

## Run

Start Docker Desktop, then:

```sh
cd ~/WeCodeAssignment2
git pull --ff-only
docker compose up --build -d
docker compose ps
```

Open http://localhost:8080. Check `curl -f http://localhost:8080/healthz` (expected `ok`). The first build downloads the base images and npm packages.

## Scope

The image builds the React frontend with the existing npm lockfile and serves the static output with Nginx. Compose currently defines only the preview web service. The browser's connect-src policy blocks requests to external services, including the original Supabase project. Account and learning-data features therefore do not work in this preview. Do not regard the health endpoint as a database or functional test.

Next: add the application backend and an isolated PostgreSQL database, connect the frontend to that stack, and verify account/learning flows. The original source contains Supabase calls rather than a SQLite backend; the database requirement needs to be mapped explicitly. Do not apply imported Supabase SQL directly to plain PostgreSQL without adapting its auth dependencies.

The original repository and hosted site are unchanged.

## Logs and stop

```sh
docker compose logs --tail=100 web
docker compose down
```

## Verification status

The agent could not build or run the image because its environment cannot access the Docker daemon socket. A successful build, healthy container and browser check are required before closing the Docker issues.
