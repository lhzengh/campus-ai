"""Own the Core database engine, ORM base, and request-scoped sessions."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from campus_ai.config import get_settings


class Base(DeclarativeBase):
    """Declarative root for all Core-owned persistence models."""

    pass


def _connect_args(database_url: str) -> dict[str, object]:
    """Apply the thread setting required by local SQLite validation runs."""

    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


settings = get_settings()
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args=_connect_args(settings.database_url),
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def get_session() -> Generator[Session, None, None]:
    """Yield one FastAPI session and always release its connection afterward."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
