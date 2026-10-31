from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_DATABASE_URL = get_settings().DATABASE_URL
# SQLite (local dev / single-instance deploys without Postgres) is accessed from FastAPI's
# threadpool, so its driver must not forbid cross-thread connection use. Postgres is unaffected.
_CONNECT_ARGS = {"check_same_thread": False} if _DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(_DATABASE_URL, pool_pre_ping=True, connect_args=_CONNECT_ARGS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
