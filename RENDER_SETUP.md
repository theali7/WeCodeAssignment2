# Render demonstration deployment

This is a fallback demonstration host while Railway signups are unavailable. Render uses render.yaml Blueprints, not Docker Compose. This is NOT proof of the assignment's literal "Docker Compose only" requirement. Issue #6 stays open until that interpretation is resolved and the public site is verified. compose.yaml remains the local app + PostgreSQL definition. The original site/repository and production Supabase must not be changed.

## Create the isolated stack

1. Sign in at https://dashboard.render.com/ with the GitHub account that owns the assignment repository.
2. Select New > Blueprint. Grant GitHub repository access to theali7/WeCodeAssignment2 only; do not select WeCode-User-Dashboard.
3. Select WeCodeAssignment2, branch main and render.yaml. Use a Blueprint name such as wecode-assignment2.
4. Review the web service and PostgreSQL database: both compute plans must say Free. This file does not authorize paid resources. Stop if Render proposes paid resources or a billing requirement, and inspect the screen.
5. Create/deploy the Blueprint. Render generates AUTH_SECRET and database credentials. DATABASE_URL references the internal URL of the new database. Do not paste the local .env or production keys. Both services use Frankfurt; ipAllowList: [] blocks external PostgreSQL connections.
6. The app listens on 0.0.0.0:8080; PORT=8080 and healthCheckPath=/api/health are configured. Startup retries temporary database connection failures a bounded number of times and applies versioned migrations.
7. Wait for Live and copy the actual HTTPS onrender.com URL shown by Render. Do not invent a URL from the service name.

## HTTPS and secrets

Render terminates HTTPS at its proxy and forwards HTTP internally. Uvicorn continues to ignore client-supplied forwarding headers. The origin guard instead uses the documented RENDER_EXTERNAL_URL variable; only that exact HTTPS origin is accepted for browser writes. PUBLIC_ORIGIN can explicitly override it for a reviewed custom domain. Invalid configured origins fail startup. Without either variable, local same-origin behavior is unchanged.

The account database is new and isolated; local/production accounts are not copied. Create a new demonstration account. OAuth and email recovery remain unconfigured and report their unavailable states.

## Verify before closing deployment work

- Actual public URL serves the current UI; /api/health returns HTTP 200 and database=postgresql.
- Registration, logout, login and refresh work over HTTPS.
- Learning Way exercise progress persists after a fresh login.
- Python, Java and SQL execute; worker dependencies load from the app origin.
- Check deployment logs without sharing secrets or access tokens.
- Confirm CI-gated auto-deploy in the dashboard and verify a subsequent successful main commit deploys. autoDeployTrigger: checksPass is configuration, not proof of working CI/CD. #8 remains open until tested end-to-end.

## Free plan limits

As checked on 2026-11-02, free web services sleep after 15 idle minutes and may take about a minute to wake. Free PostgreSQL expires 30 days after creation, becomes inaccessible and is later deleted after the grace period unless upgraded. This is a temporary demonstration, not indefinite free hosting. No paid upgrade is authorized. Record the actual database expiration from the dashboard and export any needed demonstration data before then. Use synthetic demonstration data.

Sources: https://render.com/docs/free , https://render.com/docs/blueprint-spec , https://render.com/docs/environment-variables , https://render.com/docs/web-services .
