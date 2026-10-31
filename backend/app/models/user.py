from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

import uuid

from app.models.base import Base, TimestampMixin


def new_user_id() -> str:
    return str(uuid.uuid4())


class User(Base, TimestampMixin):
    __tablename__ = "users"

    # Opaque UUID: not guessable or enumerable, unlike a sequential integer.
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_user_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Accounts created by scripts/seed_demo.py. They cannot authenticate unless DEMO_MODE=true.
    is_demo_account: Mapped[bool] = mapped_column(Boolean, default=False)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)

    # Personal
    photo_url: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(32))
    location: Mapped[str | None] = mapped_column(String(120))
    linkedin_url: Mapped[str | None] = mapped_column(String(300))
    github_url: Mapped[str | None] = mapped_column(String(300))
    portfolio_url: Mapped[str | None] = mapped_column(String(300))

    # Education
    degree: Mapped[str | None] = mapped_column(String(120))
    university: Mapped[str | None] = mapped_column(String(160))
    graduation_year: Mapped[int | None] = mapped_column(Integer)
    education_level: Mapped[str | None] = mapped_column(String(40))

    # Experience / goal
    experience_level: Mapped[str | None] = mapped_column(String(20))
    # Free text in Phase 1. Phase 2 adds role_id referencing roles.
    target_role: Mapped[str | None] = mapped_column(String(120))
    target_role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"))

    user: Mapped[User] = relationship(back_populates="profile")


class RevokedToken(Base):
    """Logout support: JWT ids that must no longer be accepted."""

    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
