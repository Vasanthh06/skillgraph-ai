from sqlalchemy import Float, ForeignKey, Integer, JSON, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SkillEmbedding(Base, TimestampMixin):
    __tablename__ = "skill_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), unique=True)
    model_name: Mapped[str] = mapped_column(String(120))
    vector: Mapped[bytes] = mapped_column(LargeBinary)


class UserEmbedding(Base, TimestampMixin):
    __tablename__ = "user_embeddings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    model_name: Mapped[str] = mapped_column(String(120))
    vector: Mapped[bytes] = mapped_column(LargeBinary)


class SearchHistory(Base, TimestampMixin):
    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    query: Mapped[str] = mapped_column(String(200))
    matched_skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"))


class UserActivity(Base, TimestampMixin):
    """Ordered event log; feeds sequential-intent modelling (Phase 11)."""

    __tablename__ = "user_activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(30))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    meta: Mapped[dict | None] = mapped_column(JSON)


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # skill|resource|project|job|interview_topic
    entity_id: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    explanation: Mapped[dict | None] = mapped_column(JSON)  # what / why / why_now / impact / next
    source: Mapped[str] = mapped_column(String(20), default="rules")  # rules | demo | model
