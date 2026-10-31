from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserSkill(Base, TimestampMixin):
    """Derived, per-user skill estimate (recomputed by the knowledge engine in Phase 4).

    `score` remains the single authoritative proficiency estimate. The calibration/review columns are a
    read cache of the latest derived intelligence for this skill; attempt and schedule history stay in
    `InterviewAttempt` / `SkillRecallSchedule`, so nothing is overwritten.
    """

    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 0..100
    level: Mapped[str] = mapped_column(String(20), default="none")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # 0..1
    self_confidence: Mapped[float | None] = mapped_column(Float)  # user's own rating, 0..100, kept distinct
    demonstrated_score: Mapped[float | None] = mapped_column(Float)  # objectively scored attempts only
    calibration_status: Mapped[str] = mapped_column(String(30), default="insufficient_evidence")
    last_evidence_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserSkillAssessment(Base, TimestampMixin):
    __tablename__ = "user_skill_assessments"
    __table_args__ = (UniqueConstraint("user_id", "skill_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    self_level: Mapped[str | None] = mapped_column(String(20))
    checklist: Mapped[dict | None] = mapped_column(JSON)  # {"Loops": true, ...}
    test_score: Mapped[float | None] = mapped_column(Float)
    # Explicit "how confident are you that you could use this independently?" rating (0..100). Separate
    # from self_level: calibration compares this (or the mapped level) with demonstrated performance.
    confidence_rating: Mapped[float | None] = mapped_column(Float)


class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(30))  # resume|assessment|project|certification|learning|interview
    strength: Mapped[float] = mapped_column(Float, default=0.0)
    detail: Mapped[str | None] = mapped_column(Text)


class Certification(Base, TimestampMixin):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200))
    issuer: Mapped[str | None] = mapped_column(String(160))
    issued_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    credential_url: Mapped[str | None] = mapped_column(String(400))
