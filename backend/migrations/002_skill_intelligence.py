"""Migration 002: integrated skill intelligence (bottleneck / calibration / recall).

Adds confidence & calibration fields, attempt purpose/topic history, learning completion times and
the per-skill recall schedule table. Data-preserving and idempotent - see
`app.core.migrations.migrate_intelligence`. Run with:  python scripts/migrate_db.py
"""
from app.core.migrations import migrate_intelligence


def upgrade(engine):
    return migrate_intelligence(engine)
