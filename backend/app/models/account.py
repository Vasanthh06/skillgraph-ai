"""Additive account lifecycle tables; no existing user columns are replaced."""
from datetime import datetime
from sqlalchemy import String, ForeignKey, Boolean, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class AccountSecurity(Base, TimestampMixin):
    __tablename__ = "account_security"
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    valid_after: Mapped[int] = mapped_column(Integer, default=0)
    consent_version: Mapped[str | None] = mapped_column(String(40))
    adult_attested: Mapped[bool] = mapped_column(Boolean, default=False)


class AccountToken(Base):
    __tablename__ = "account_tokens"
    digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(20))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class EmailDelivery(Base, TimestampMixin):
    __tablename__ = "email_deliveries"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    provider_id: Mapped[str | None] = mapped_column(String(120))
