"""Upgrade an existing SkillGraph database in place (run from the repo root).

    python scripts/migrate_db.py

Creates any missing tables, then applies the data-preserving migrations in
`app.core.migrations`. Existing users, progress, attempts and schedules are kept.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import engine  # noqa: E402
from app.core.migrations import migrate_intelligence  # noqa: E402
from app.models import Base  # noqa: E402

if __name__ == "__main__":
    Base.metadata.create_all(engine)  # missing tables only; existing tables are upgraded below
    actions = migrate_intelligence(engine)
    Base.metadata.create_all(engine)
    print("Database is up to date." if not actions else "Applied:\n- " + "\n- ".join(actions))
