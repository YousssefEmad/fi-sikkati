"""Async SQLAlchemy engine, session factory and declarative base (ADR-0014).

One ``AsyncSession`` per request is provided by :func:`get_db_session`; it commits when the
request handler returns normally and rolls back on any exception. Repositories never commit.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import Settings

# Deterministic constraint names make Alembic autogenerate diffs stable and reviewable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base shared by every module's ``models.py``."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        str(settings.database_url),
        pool_size=settings.database_pool_size,
        pool_pre_ping=True,
        echo=settings.database_echo,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


class Database:
    """Holds the engine and session factory for the lifetime of the process."""

    def __init__(self, settings: Settings) -> None:
        self.engine = create_engine(settings)
        self.session_factory = create_session_factory(self.engine)

    async def dispose(self) -> None:
        await self.engine.dispose()

    async def ping(self) -> None:
        """Raise if the database is unreachable (used by readiness checks)."""
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def session(self) -> AsyncIterator[AsyncSession]:
        """Unit of work: commit on success, roll back on error, always close."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


def get_database(request: Request) -> Database:
    database = request.app.state.database
    if not isinstance(database, Database):  # pragma: no cover — programming error
        msg = "Database is not initialised on app.state"
        raise TypeError(msg)
    return database


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding the per-request unit of work."""
    async for session in get_database(request).session():
        yield session
