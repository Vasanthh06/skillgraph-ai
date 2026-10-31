from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Profile, RevokedToken, User


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_by_id(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def create_user_with_profile(db: Session, *, full_name: str, email: str, hashed_password: str) -> User:
    """User and profile are created in one transaction (spec §5)."""
    user = User(full_name=full_name, email=email.lower(), hashed_password=hashed_password)
    user.profile = Profile()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def revoke_token(db: Session, jti: str, expires_at: datetime) -> None:
    if db.get(RevokedToken, jti) is None:
        db.add(RevokedToken(jti=jti, expires_at=expires_at))
    # opportunistic cleanup of expired rows
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < datetime.now(timezone.utc)))
    db.commit()


def is_revoked(db: Session, jti: str) -> bool:
    return db.get(RevokedToken, jti) is not None
