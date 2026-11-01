"""Writing audit entries."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.ids import uuid7
from app.modules.audit.models import ActorType, AuditAction, AuditLog

IndependentWork = Callable[[AsyncSession], Awaitable[None]]


class AuditLogWriter:
    """Adds entries to the current unit of work; the request's commit makes them durable.

    No ``commit`` here on purpose: an audit entry must become visible exactly when — and only
    when — the change it describes does.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(
        self,
        action: AuditAction,
        *,
        actor_type: ActorType,
        actor_id: UUID | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        request_id: str | None = None,
        ip_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._db.add(
            AuditLog(
                id=uuid7(),
                actor_type=actor_type,
                actor_id=actor_id,
                action=action.value,
                target_type=target_type,
                target_id=target_id,
                request_id=request_id,
                ip_hash=ip_hash,
                payload=metadata or {},
            )
        )
        await self._db.flush()


class IndependentAuditLogWriter:
    """Writes that must outlive a rolled-back request.

    Failed sign-in attempts and refresh-token reuse raise after they have been recorded; the
    per-request unit of work would otherwise undo the very evidence we need to keep.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def in_own_transaction(self, work: IndependentWork) -> None:
        """Run ``work`` on a fresh session and commit it, regardless of the request's fate."""
        async with self._session_factory() as db:
            await work(db)
            await db.commit()

    async def record(
        self,
        action: AuditAction,
        *,
        actor_type: ActorType,
        actor_id: UUID | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        request_id: str | None = None,
        ip_hash: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        async def write(db: AsyncSession) -> None:
            await AuditLogWriter(db).record(
                action,
                actor_type=actor_type,
                actor_id=actor_id,
                target_type=target_type,
                target_id=target_id,
                request_id=request_id,
                ip_hash=ip_hash,
                metadata=metadata,
            )

        await self.in_own_transaction(write)
