import uuid
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

import bcrypt

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
import jwt

from app.core.config import get_settings

BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    if len(password) > 128:
        raise ValueError("password too long")
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    if hashed.startswith("$argon2"):
        try:
            return _hasher.verify(hashed, password)
        except (VerificationError, InvalidHashError):
            return False
    raw = password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(raw, hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: str) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at)."""
    s = get_settings()
    now = datetime.now(timezone.utc)
    jti = uuid.uuid4().hex
    expires = now + timedelta(minutes=s.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = jwt.encode(
        {"sub": str(user_id), "jti": jti, "iat": now, "exp": expires},
        s.SECRET_KEY,
        algorithm=s.JWT_ALGORITHM,
    )
    return token, jti, expires


def decode_token(token: str) -> dict:
    """Raises jwt.PyJWTError on any problem."""
    s = get_settings()
    return jwt.decode(token, s.SECRET_KEY, algorithms=[s.JWT_ALGORITHM], options={"require": ["sub", "jti", "iat", "exp"]})
