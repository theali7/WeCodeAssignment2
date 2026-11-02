# WeCode Assignment 2

Live demonstration: https://wecode-assignment2.onrender.com

## Run locally

Start Docker Desktop, then:

```sh
python3 scripts/setup_env.py
docker compose up --build -d
```

Open http://localhost:8080 and create a new assignment account. Stop with `docker compose down` to preserve database records. Never commit .env.

## Architecture and instructions

A single application Dockerfile serves recovered static frontend assets and FastAPI. Compose adds an isolated PostgreSQL 17 database with persistent storage and versioned migrations.

- [Local setup and limitations](DOCKER_SETUP.md)
- [Playwright tests](e2e/README.md)
- [Render deployment](RENDER_SETUP.md)
- [Frontend recovery](recovered-publication/RECOVERY.md)
- [Assignment issues](https://github.com/theali7/WeCodeAssignment2/issues)

The original WeCode-User-Dashboard repository, original published site and production database are outside this assignment's changes. Existing production/local accounts are not copied to Render.

## Verification evidence

Commit `77fdb3e` passed:
- [Backend, security, integration and Docker checks](https://github.com/theali7/WeCodeAssignment2/actions/runs/41491467308)
- [Playwright browser tests](https://github.com/theali7/WeCodeAssignment2/actions/runs/41491467096)

The owner supplied a Render dashboard screenshot showing this same commit Live with trigger Auto-Deploy, after configuring After CI Checks Pass. The owner also confirmed registration and Learning Way progress persistence on the public site. This is manual public-host evidence; the Playwright runs use disposable CI databases, not the public database.

## Outstanding assignment requirements

- AWS + CloudFormation or Google Cloud + Terraform has **not** been deployed. The owner deferred this step after AWS phone verification failed and Google Cloud requested a minimum $30 activation prepayment. Issue #7 remains open.
- Render Blueprint runs Docker but does **not** execute Docker Compose. The literal “Docker Compose only” hosting requirement remains unresolved in issue #6.
- No SQLite database was found in the tracked imported project; PostgreSQL was configured without claiming a SQLite data migration.
- Docker serves recovered publication bundles; src/ contains older editable source. Full editable-source reconciliation remains separate.
- OAuth and email recovery are not configured in this isolated assignment. Code execution is client-side practice feedback, not a trusted server judge.
- Render's free database is temporary; see RENDER_SETUP.md for expiry and backup guidance.

Do not treat this repository as complete fulfillment of every assignment requirement until outstanding issues are resolved.
