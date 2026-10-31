from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories import users as repo
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut

# Used to equalise timing when the email is unknown (avoids user enumeration by latency).
_DUMMY_HASH = hash_password("dummy-password-1")


class EmailTaken(Exception):
    pass


class InvalidCredentials(Exception):
    pass


def _token_response(user) -> TokenOut:
    token, _jti, expires = create_access_token(user.id)
    return TokenOut(access_token=token, expires_at=expires.isoformat(), user=UserOut.model_validate(user))


def register(db: Session, data: RegisterIn) -> TokenOut:
    if repo.get_by_email(db, data.email):
        raise EmailTaken()
    user = repo.create_user_with_profile(
        db, full_name=data.full_name, email=data.email, hashed_password=hash_password(data.password)
    )
    return _token_response(user)


def login(db: Session, data: LoginIn) -> TokenOut:
    user = repo.get_by_email(db, data.email)
    if user is None:
        verify_password(data.password, _DUMMY_HASH)
        raise InvalidCredentials()
    if not verify_password(data.password, user.hashed_password) or not user.is_active:
        raise InvalidCredentials()
    if user.is_demo_account and not get_settings().DEMO_MODE:
        raise InvalidCredentials()  # same message: don't reveal that a demo account exists
    return _token_response(user)


def logout(db: Session, jti: str, exp: int) -> None:
    repo.revoke_token(db, jti, datetime.fromtimestamp(exp, tz=timezone.utc))
