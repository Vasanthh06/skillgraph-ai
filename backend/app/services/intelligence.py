"""Database writes for the integrated intelligence loop (recall scheduling + evidence history).

The calculations live in `app.engine.intelligence`; this module only persists their inputs/outputs,
always through `UserScope`, so schedules and evidence can never leak between users.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.engine import intelligence as INT
from app.models import Evidence, SkillRecallSchedule
from app.repositories.scoped import UserScope
from app.services.seed import skill_maps


def skill_intelligence(analysis, slug: str) -> dict:
    """The per-skill intelligence block views embed (estimate + calibration + bottleneck + review)."""
    intel = getattr(analysis, "intelligence", None) or {}
    block = (intel.get("by_skill") or {}).get(slug) or {}
    est = analysis.estimates.get(slug)
    return {
        "slug": slug, "name": analysis.cat.name(slug),
        "estimate": {"score": round(est.score) if est else 0, "level": est.level if est else "none",
                     "confidence": est.confidence if est else 0.0, "sources": est.sources if est else {},
                     "capped": bool(est and est.capped)},
        "calibration": block.get("calibration"), "bottleneck": block.get("bottleneck"),
        "review": block.get("review"),
        "evidence_history": (getattr(analysis, "evidence_history", {}) or {}).get(slug, []),
    }


def ensure_schedule(db: Session, user_id: str, slug: str, *, source: str = "learning",
                    when: datetime | None = None) -> SkillRecallSchedule:
    """Create (or keep) the first review for a skill the user just marked learned. An existing
    schedule is never reset by re-completing the same activity."""
    to_id, _ = skill_maps(db)
    now = INT.as_utc(when) or datetime.now(timezone.utc)
    row = UserScope(db, user_id).upsert(SkillRecallSchedule, {"skill_id": to_id[slug]})
    if row.learned_at is None:
        row.learned_at = now
    if row.next_review_at is None:
        row.next_review_at = now + timedelta(days=INT.REVIEW_INTERVALS[0])
        row.interval_days = float(INT.REVIEW_INTERVALS[0])
    row.source = source or row.source or "learning"
    return row


def record_review(db: Session, user_id: str, slug: str, *, score: float, weak_topics: list[str],
                  source: str = "recall", when: datetime | None = None) -> dict:
    """Advance/shorten one skill's review schedule from a completed knowledge check."""
    to_id, _ = skill_maps(db)
    now = INT.as_utc(when) or datetime.now(timezone.utc)
    row = UserScope(db, user_id).upsert(SkillRecallSchedule, {"skill_id": to_id[slug]})
    stage, days, result, reason = INT.next_stage_and_interval(row.review_stage, float(score), row.interval_days)
    if row.learned_at is None:
        row.learned_at = now
    row.last_reviewed_at, row.next_review_at = now, now + timedelta(days=days)
    row.review_stage, row.interval_days = stage, float(days)
    row.review_count = int(row.review_count or 0) + 1
    if result == "strong":
        row.successful_reviews = int(row.successful_reviews or 0) + 1
    row.last_score, row.last_result = float(score), result
    row.weak_topics = [str(t)[:160] for t in weak_topics[:6]]
    row.source = source
    return {"slug": slug, "score": round(float(score)), "result": result, "reason": reason,
            "next_review_at": INT.iso(row.next_review_at), "interval_days": days,
            "review_stage": stage, "weak_topics": row.weak_topics}


def add_evidence(db: Session, user_id: str, slug: str, *, source: str, strength: float, detail: str) -> None:
    """Append (never overwrite) one evidence-history entry for the skill."""
    to_id, _ = skill_maps(db)
    UserScope(db, user_id).add(Evidence(skill_id=to_id[slug], source=source[:30],
                                        strength=max(0.0, min(100.0, float(strength))), detail=detail[:1000]))
