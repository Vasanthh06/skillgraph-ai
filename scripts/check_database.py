"""Read-only connectivity check. Does not print URL, credentials or driver error text."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from sqlalchemy import text
from app.core.database import engine
try:
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT 1')) == 1
except Exception:
    raise SystemExit('Database connectivity failed. Check private environment, network and TLS settings.') from None
print('Database SELECT 1 succeeded.')
