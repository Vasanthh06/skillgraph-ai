# Setup and deployment guide

## Status and prerequisites
This is an audited academic working revision, not a completed public production rollout. Python 3.12 recommended; Node 22; PostgreSQL for production. SQLite is used only for isolated local checks here. Do not use the preview database or synthetic accounts for production. No Neon credentials or email key was supplied.

## 1. Extract and install
Unzip `Skill_Graph_AI_Final_Project.zip`; enter `skillgraph-ai`. `preservation/` contains immutable original versions of modified files for comparison, not importable application code.

Linux/macOS:
```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm ci && cd ..
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Windows PowerShell:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
cd frontend; npm ci; cd ..
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Put the generated secret into `SECRET_KEY`, privately. Never send it to frontend variables or commit `.env`.

## 2. Environment
- `DATABASE_URL`: required deployment-specific SQLAlchemy URL. SQLite local example: `sqlite:///./skillgraph-local.db` (path relative to process working directory; prefer absolute path).
- `SECRET_KEY`: required random 32+ characters; keep `DEMO_MODE=false`. Demo mode deliberately retains legacy short-password test policy; never enable it for public use.
- `APP_URL`: trusted public frontend origin, no user-controlled request hostname. Local: `http://localhost:5173`; production: HTTPS URL.
- `COOKIE_SECURE`: false only on local HTTP; true on production HTTPS.
- `CORS_ORIGINS`: explicit trusted origins; same-origin routing is recommended. Cookies use same-origin fetch and SameSite=Lax; do not configure a separate frontend/API origin without revisiting cookie/CSRF design.
- `UPLOAD_DIR`, upload size limits: private persistent server storage; never serve files as a public directory.
- `RESEND_API_KEY`, `EMAIL_FROM`: optional until email is enabled, server-only. Missing config is displayed in roadmap delivery controls.
- `ADMIN_BOOTSTRAP_ENABLED`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`: one-time operator command only; default disabled. Remove password after provisioning.
- `YOUTUBE_API_KEY`: optional server-only; default resource search links work without it.
- `RATE_LIMIT_ENABLED`, auth limit/window: enabled for public use. Current limiter is process-local; use an edge/shared limiter before multiworker deployment.

## 3. Neon
1. Create a project at https://neon.tech/ and select an appropriate region.
2. Create/select the application's database and restricted runtime role. Use a separate migration role if operationally practical.
3. Copy the pooled connection URL from Neon's Connect dialog. Store it privately in `DATABASE_URL`. For psycopg2 use `postgresql+psycopg2://...?...sslmode=require`; retain supplied TLS options. Percent-encode reserved password characters.
4. Back up an existing database first. Do not point scripts at another application's database.
5. From the repository root, run `python scripts/init_db.py` for a new database, or `python scripts/migrate_db.py` for an existing one. These scripts register the additive account-security/token/delivery tables. Existing duplicate assessments now stop migration rather than deleting rows; obtain approval for a merge strategy.
6. Verify with `python scripts/check_database.py`. This executes only `SELECT 1` and prints no credentials.
7. Run integration tests against an isolated disposable PostgreSQL branch before release. That has NOT been executed here.

No existing database was discarded or migrated live. SQLAlchemy uses `pool_pre_ping`; Neon pooling is server-side through its pooled hostname. Establish pool sizing/connection budgets for your chosen worker count before scaling. Local SQLite tests do not validate PostgreSQL locking, TLS, constraints or migration behavior.

## 4. Provision administrator
After schema setup, temporarily set all three bootstrap variables in the private server environment. Then:
```sh
python scripts/bootstrap_admin.py
```
The command refuses an existing email and never resets its password or silently promotes it. It hashes a new password using Argon2id. Disable bootstrap and remove `ADMIN_PASSWORD` immediately. Use normal email verification; admins are not automatically email-verified. Visit `/admin` after sign-in. Read-only account listing is implemented, not a complete operations console.

## 5. Email
Choose Resend, verify your sender domain using its DNS instructions, create a restricted API key, and configure `EMAIL_FROM` on that verified domain. Sandbox `resend.dev` delivery is restricted; it is not unrestricted free production sending. Restart backend after changing environment.

Register an adult synthetic account, open Roadmap, request verification, follow the received link, then request `Email My Roadmap`. Forgot-password is linked from Login. Account links use a URL fragment (not query string), cleared from browser history on page initialization. Tokens expire after 20 minutes and are stored only as SHA-256 digests. Never enable analytics on token handling pages without additional review.

The provider boundary is `backend/app/services/email_service.py`; replace that adapter for Brevo. Mock provider tests exist; real delivery and sender verification remain NOT CONFIGURED. Sent status means API acceptance, not inbox delivery; webhooks/bounce processing and durable outbox recovery remain future work. Do not retry a stuck pending delivery by inventing new IDs; investigate with the operator. Reset email requests return generic responses even when provider configuration is absent.

## 6. Local start (two terminals)
From root with environment configured:
```sh
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-proxy-headers
```
Second terminal:
```sh
cd frontend
npm run dev -- --host 0.0.0.0
```
Open http://localhost:5173. Browser requests `/api` through Vite's server-side proxy. `--no-proxy-headers` is deliberate: never trust arbitrary forwarding headers. With this safe default the proxy shares a rate bucket; add a trusted edge rate limiter and explicitly configured proxy trust before internet deployment.

## 7. Test and build
```sh
PYTHONPATH=backend pytest -q
cd frontend
npm run typecheck
npm run build
npm audit
cd ..
pip-audit -r backend/requirements.txt
```
PowerShell: set `$env:PYTHONPATH="backend"` before `pytest -q`. Install `pip-audit` separately if needed. For browser checks: `pip install playwright`, `python -m playwright install --with-deps chromium`, run local servers, then `python scripts/browser_check.py`. It creates synthetic accounts, uses real Chromium and never sends real emails. Some browser setup actions use authenticated API calls; it is not a fully UI-driven E2E suite.

## 8. Production candidate
```sh
docker compose -f deploy/compose.production.yml build
docker compose -f deploy/compose.production.yml run --rm backend python ../scripts/init_db.py
docker compose -f deploy/compose.production.yml up -d
```
Production compose is prepared, NOT executed here. Terminate HTTPS upstream, set APP_URL/COOKIE_SECURE, and expose only frontend port 8080 to that gateway. Backend must stay private. Nginx serves built assets and SPA direct routes and proxies `/api`. `/health` on private backend is liveness only, not DB readiness. Configure monitoring, backups, upload persistence, limited logs, retention, secrets management, upstream request limits and a shared authentication limiter. Do not use the original development compose as a production security profile.

## Rollback and troubleshooting
Retain prior source/image and database backup. Additive schema can remain on code rollback; do not drop new tables. If migration finds duplicates it stops: do not bypass by deleting rows. Cookies missing: check same origin, HTTPS/Secure flags, proxy scheme and browser restrictions. Email missing: verify provider dashboard/domain/quota without printing API keys or tokens. Never blindly retry after ambiguous provider acceptance. Restore original files from preservation only after reviewing changed security contracts and schema dependencies.

## Release blockers
Publish operator/grievance contact and reviewed privacy/terms; implement practical account deletion and retention; audit all admin reporting needs; real PostgreSQL/Neon tests; verify email delivery; resolve residual dependency findings; independent security/accessibility review and physical-device checks. Do not present this revision as fully compliant or vulnerability-free.
