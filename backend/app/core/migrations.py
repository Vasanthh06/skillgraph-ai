"""Idempotent, data-preserving schema migrations (the project predates Alembic; see scripts/).

`migrate_intelligence` upgrades an existing SkillGraph database for the integrated intelligence
features: it only ADDS columns/tables/indexes and backfills from data already stored. It never drops
a table or column, and duplicate assessment rows are merged (newest value wins, gaps filled from
older rows) before the new uniqueness rule is applied - so no user's progress is lost.
"""
from __future__ import annotations

import json

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _ts(engine: Engine) -> str:
    return "TIMESTAMP WITH TIME ZONE" if engine.dialect.name == "postgresql" else "TIMESTAMP"


def _columns(engine: Engine) -> dict[str, dict[str, str]]:
    ts = _ts(engine)
    return {
        "user_skills": {
            "self_confidence": "FLOAT", "demonstrated_score": "FLOAT",
            "calibration_status": "VARCHAR(30) DEFAULT 'insufficient_evidence'",
            "last_evidence_at": ts, "next_review_at": ts,
        },
        "user_skill_assessments": {"confidence_rating": "FLOAT"},
        "interview_attempts": {
            "purpose": "VARCHAR(20) DEFAULT 'interview'", "session_id": "VARCHAR(36)",
            "topic": "VARCHAR(200)", "is_correct": "BOOLEAN",
        },
        "user_progress": {"completed_at": ts},
    }


def _dedupe_assessments(conn) -> int:
    """Merge duplicate (user, skill) assessment rows so the unique index can be created safely."""
    merged = 0
    pairs = conn.execute(text(
        "SELECT user_id, skill_id FROM user_skill_assessments GROUP BY user_id, skill_id HAVING COUNT(*) > 1")).all()
    if pairs:
        raise RuntimeError("Duplicate assessments found; migration stopped without deleting records. Back up and obtain operator approval for a merge plan.")
    fields = ("self_level", "checklist", "test_score", "confidence_rating")
    for user_id, skill_id in pairs:
        rows = conn.execute(text(
            "SELECT * FROM user_skill_assessments WHERE user_id = :u AND skill_id = :s "
            "ORDER BY updated_at DESC, id DESC"), {"u": user_id, "s": skill_id}).mappings().all()
        keep, fill = dict(rows[0]), {}
        for f in fields:
            if keep.get(f) is None:
                fill[f] = next((r[f] for r in rows[1:] if r.get(f) is not None), None)
        fill = {k: v for k, v in fill.items() if v is not None}
        if fill:
            # Raw-SQL binds for JSON columns need text on some drivers (PostgreSQL in particular).
            bound = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in fill.items()}
            conn.execute(text("UPDATE user_skill_assessments SET " + ", ".join(f"{k} = :{k}" for k in fill)
                              + " WHERE id = :id"), {**bound, "id": keep["id"]})
        for r in rows[1:]:
            conn.execute(text("DELETE FROM user_skill_assessments WHERE id = :id"), {"id": r["id"]})
            merged += 1
    return merged


def _ensure_index(conn, insp, table: str, name: str, columns: str, *, unique: bool = False) -> bool:
    existing = {ix["name"] for ix in insp.get_indexes(table)}
    if name in existing:
        return False
    if unique and any(ix.get("unique") and set(ix["column_names"]) == {c.strip() for c in columns.split(",")}
                      for ix in insp.get_indexes(table)):
        return False
    conn.execute(text(f"CREATE {'UNIQUE ' if unique else ''}INDEX IF NOT EXISTS {name} ON {table} ({columns})"))
    return True


def migrate_intelligence(engine: Engine) -> list[str]:
    """Apply the skill-intelligence schema upgrade. Returns the actions taken (empty if up to date)."""
    from app.models import SkillRecallSchedule  # local import: models import this package's Base first

    actions: list[str] = []
    with engine.begin() as conn:
        insp = inspect(conn)
        tables = set(insp.get_table_names())
        for table, cols in _columns(engine).items():
            if table not in tables:
                continue  # a fresh database gets the final schema from create_all instead
            have = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols.items():
                if name not in have:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                    actions.append(f"added {table}.{name}")
        if "skill_recall_schedules" not in tables:
            SkillRecallSchedule.__table__.create(bind=conn, checkfirst=True)
            actions.append("created skill_recall_schedules")
        insp = inspect(conn)  # refresh after DDL
        if "interview_attempts" in tables:
            conn.execute(text("UPDATE interview_attempts SET purpose = 'interview' WHERE purpose IS NULL"))
            if _ensure_index(conn, insp, "interview_attempts", "ix_interview_attempts_purpose", "purpose"):
                actions.append("indexed interview_attempts.purpose")
            if _ensure_index(conn, insp, "interview_attempts", "ix_interview_attempts_session_id", "session_id"):
                actions.append("indexed interview_attempts.session_id")
        if "user_skills" in tables:
            conn.execute(text("UPDATE user_skills SET calibration_status = 'insufficient_evidence' WHERE calibration_status IS NULL"))
        if "user_progress" in tables:
            done = "completed IS TRUE" if engine.dialect.name == "postgresql" else "completed = 1"
            conn.execute(text(f"UPDATE user_progress SET completed_at = updated_at WHERE completed_at IS NULL AND {done}"))
        if "user_skill_assessments" in tables:
            n = _dedupe_assessments(conn)
            if n:
                actions.append(f"merged {n} duplicate assessment row(s)")
            if _ensure_index(conn, inspect(conn), "user_skill_assessments",
                             "uq_user_skill_assessments_user_skill", "user_id, skill_id", unique=True):
                actions.append("added uniqueness on user_skill_assessments(user_id, skill_id)")
    return actions
