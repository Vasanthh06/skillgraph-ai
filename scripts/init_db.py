"""Create all tables and seed the curated catalog. Run from repo root:  python scripts/init_db.py

create_all is used for simplicity; introduce Alembic before the first production deploy.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal, engine  # noqa: E402
from app.core.migrations import migrate_intelligence  # noqa: E402
from app.models import Base  # noqa: E402
from app.services.seed import ensure_seeded  # noqa: E402

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    migrate_intelligence(engine)  # harmless on a fresh schema; upgrades an older one in place
    with SessionLocal() as db:
        ensure_seeded(db)
    print(f"Created {len(Base.metadata.tables)} tables and seeded the catalog.")
