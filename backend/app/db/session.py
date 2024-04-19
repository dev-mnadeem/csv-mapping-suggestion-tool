"""Engine, session factory and schema creation.

SQLite is enough here: the only table is an append-only log of suggestion
runs. Point ``DATABASE_URL`` at Postgres and nothing else has to change.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings

SQLITE_PREFIX = "sqlite:///"


def build_engine(settings: Settings) -> Engine:
    """Create the engine, making the SQLite parent directory if needed."""
    url = settings.database_url
    connect_args: dict[str, object] = {}
    if url.startswith(SQLITE_PREFIX):
        path = Path(url.removeprefix(SQLITE_PREFIX))
        if path.name != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        # FastAPI serves requests from a threadpool, and SQLite objects
        # are otherwise pinned to the thread that created them.
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args, future=True)


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Return the process-wide engine, creating it on first use."""
    global _engine
    if _engine is None:
        _engine = build_engine(get_settings())
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def init_db() -> None:
    """Create any missing tables. Safe to call on every startup."""
    from app.db import models

    models.Base.metadata.create_all(bind=get_engine())


def session_scope() -> Iterator[Session]:
    """FastAPI dependency yielding a session that always gets closed."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def reset_engine() -> None:
    """Drop the cached engine. Used by the tests between databases."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
