# Docker: recovered published frontend

This remains an intermediate step for issues #2, #3 and #4. The backend and isolated PostgreSQL integration are not complete.

## Run

Start Docker Desktop, then:

```sh
cd ~/WeCodeAssignment2
git pull --ff-only
docker compose up --build -d
docker compose ps
```

Open http://localhost:8080. `curl -f http://localhost:8080/healthz` should return `ok`.

The default `preview` target serves recovered-publication/, captured from the published frontend, including the Problems, Learn Languages and Learning Way modules. See recovered-publication/RECOVERY.md for provenance and limitations. Original older editable React code remains in src/. To build that older version explicitly, use `docker build --target source-preview -t wecode-old-source .`.

External connections remain blocked by the existing CSP, including calls to production Supabase. Account and remote learning-data features therefore do not work locally. This is intentional isolation while the assignment backend is being prepared; it is not a completed full-stack deployment.

```sh
docker compose logs --tail=100 web
docker compose down
```

The agent verified JavaScript syntax, relative imports and the dependency map, but could not verify the Docker build/run because access to the Docker daemon is unavailable in its execution environment. The recovered stylesheet references an unavailable Gilroy-Black.ttf weight; other captured weights are included.
