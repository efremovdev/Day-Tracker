"""Database layer (SQLite + SQLAlchemy 2.0, async via aiosqlite).

For the P1 skeleton there are no domain tables yet — ``init_db`` just creates the
database file and runs ``create_all`` so the schema-bootstrap is in place. Models
are added per phase (profile & targets in P2, meals in P3, ...). Each new model
subclasses :class:`Base` and is then picked up automatically by ``create_all``.
"""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import Settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine(settings: Settings) -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url)
    return _engine


def get_sessionmaker(settings: Settings) -> async_sessionmaker[AsyncSession]:
    """Return the process-wide async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(settings), expire_on_commit=False)
    return _session_factory


async def init_db(settings: Settings) -> None:
    """Create the database file (and any registered tables) on startup."""
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = get_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database ready at %s", settings.database_path)


async def dispose_engine() -> None:
    """Dispose the engine and reset module state (clean shutdown)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
