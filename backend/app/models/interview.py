from sqlalchemy import Boolean, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class InterviewQuestion(Base, TimestampMixin):
    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str | None] = mapped_column(String(60), unique=True, index=True)
    skill_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id", ondelete="SET NULL"), index=True)
    category: Mapped[str] = mapped_column(String(30))  # technical|coding|mcq|scenario|behavioral|project|hr
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[list | None] = mapped_column(JSON)
    answer_key: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)


class InterviewAttempt(Base, TimestampMixin):
    __tablename__ = "interview_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("interview_questions.id", ondelete="CASCADE"))
    answer: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float | None] = mapped_column(Float)
    # Why this attempt was made. The same question bank serves interview practice, confidence
    # calibration checks and spaced-recall reviews; every attempt stays an immutable history row.
    purpose: Mapped[str] = mapped_column(String(20), default="interview", index=True)  # interview|calibration|recall
    session_id: Mapped[str | None] = mapped_column(String(36), index=True)
    topic: Mapped[str | None] = mapped_column(String(200))  # the question/topic this attempt evidences
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
