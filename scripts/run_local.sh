#!/usr/bin/env bash
# One-command local run (no Docker): backend :8000 + frontend :5173.
#
#   bash scripts/run_local.sh
#
# Creates a git-ignored repo-root .env (with a generated SECRET_KEY and a SQLite
# DATABASE_URL) the first time only, creates/seeds the database, installs frontend
# dependencies if needed, then starts both servers. Login needs BOTH servers:
# the login page's "Can't reach the server" means the backend isn't running.
# First visit: open http://localhost:5173 and use "Create an account" — accounts
# live in your local database, so demo logins from any hosted preview don't exist here.
# Stop with Ctrl-C (both servers are stopped together).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
  cat > .env <<EOF
DEMO_MODE=false
SECRET_KEY=${SECRET}
DATABASE_URL=sqlite:///data/skillgraph.db
CORS_ORIGINS=http://localhost:5173
UPLOAD_DIR=${ROOT}/backend/uploads
EOF
  echo "Created .env (generated SECRET_KEY, SQLite at data/skillgraph.db)"
fi

mkdir -p data backend/uploads
# Export everything in .env so uvicorn/init_db see the same values from any cwd.
set -a; . ./.env; set +a
export PYTHONPATH="${ROOT}/backend"

python -c 'import fastapi' >/dev/null 2>&1 || pip install -r backend/requirements.txt
python scripts/init_db.py
python scripts/migrate_db.py   # upgrades an existing database in place (no-op when current)

if [ ! -d frontend/node_modules ]; then
  (cd frontend && (npm ci || npm install))
fi

(cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000) &
BACK_PID=$!
trap 'kill ${BACK_PID} 2>/dev/null || true' EXIT INT TERM
(cd frontend && npm run dev) &
FRONT_PID=$!
trap 'kill ${BACK_PID} ${FRONT_PID} 2>/dev/null || true' EXIT INT TERM

sleep 2
curl -fsS http://127.0.0.1:8000/health >/dev/null && echo "Backend healthy: http://127.0.0.1:8000/health"
echo "Open http://localhost:5173 and Create an account (or log in). Ctrl-C stops both servers."
wait
