"""Ports for checks that a lower module must not import from a higher one.

``users`` must not import ``trips`` or ``bookings``, and ``trips`` must not import ``bookings``
(import-linter layers). The composition root binds the implementations on ``app.state``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


class DeletionGuard(Protocol):
    """Return human-readable blockers that prevent ``DELETE /me`` (BR-ACC-07)."""

    async def blockers(self, db: AsyncSession, user_id: UUID) -> tuple[str, ...]: ...


class NoopDeletionGuard:
    async def blockers(self, db: AsyncSession, user_id: UUID) -> tuple[str, ...]:
        del db, user_id
        return ()


class CompositeDeletionGuard:
    """Run every phase's deletion check and concatenate the reasons."""

    def __init__(self, guards: tuple[DeletionGuard, ...]) -> None:
        self._guards = guards

    async def blockers(self, db: AsyncSession, user_id: UUID) -> tuple[str, ...]:
        found: list[str] = []
        for guard in self._guards:
            found.extend(await guard.blockers(db, user_id))
        return tuple(found)


_ATTR = "deletion_guard"


def bind_deletion_guard(app_state: object, guard: DeletionGuard) -> None:
    setattr(app_state, _ATTR, guard)


def get_deletion_guard(request: Request) -> DeletionGuard:
    guard = getattr(request.app.state, _ATTR, None)
    if guard is None:
        return NoopDeletionGuard()
    return guard  # type: ignore[no-any-return]


class CancellationStats(Protocol):
    """How many of this user's own cancellations fall inside the profile window (OD-008)."""

    async def count_recent(self, db: AsyncSession, user_id: UUID, *, days: int) -> int: ...


class NoopCancellationStats:
    async def count_recent(self, db: AsyncSession, user_id: UUID, *, days: int) -> int:
        del db, user_id, days
        return 0


_STATS = "cancellation_stats"


def bind_cancellation_stats(app_state: object, stats: CancellationStats) -> None:
    setattr(app_state, _STATS, stats)


def get_cancellation_stats(request: Request) -> CancellationStats:
    stats = getattr(request.app.state, _STATS, None)
    if stats is None:
        return NoopCancellationStats()
    return stats  # type: ignore[no-any-return]


class BookingBridge(Protocol):
    """Seat-adjacent effects ``trips`` must apply without importing ``bookings``."""

    async def on_trip_cancelled(
        self, trip_id: UUID, *, cancelled_by: str, now: datetime
    ) -> None: ...

    async def on_trip_completed(self, trip_id: UUID, *, now: datetime) -> None: ...

    async def is_accepted_passenger(self, trip_id: UUID, user_id: UUID) -> bool: ...

    async def list_passenger_trip_ids(
        self,
        user_id: UUID,
        *,
        statuses: frozenset[str] | None,
        before: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[UUID]: ...

    async def passenger_ids(self, trip_id: UUID, *, include_pending: bool) -> tuple[UUID, ...]:
        """Accepted passengers of a trip (plus pending requesters when asked)."""
        ...


class NoopBookingBridge:
    async def on_trip_cancelled(self, trip_id: UUID, *, cancelled_by: str, now: datetime) -> None:
        del trip_id, cancelled_by, now

    async def on_trip_completed(self, trip_id: UUID, *, now: datetime) -> None:
        del trip_id, now

    async def is_accepted_passenger(self, trip_id: UUID, user_id: UUID) -> bool:
        del trip_id, user_id
        return False

    async def list_passenger_trip_ids(
        self,
        user_id: UUID,
        *,
        statuses: frozenset[str] | None,
        before: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[UUID]:
        del user_id, statuses, before, limit
        return []

    async def passenger_ids(self, trip_id: UUID, *, include_pending: bool) -> tuple[UUID, ...]:
        del trip_id, include_pending
        return ()


_BRIDGE = "booking_bridge_factory"


def bind_booking_bridge_factory(
    app_state: object, factory: Callable[[AsyncSession], BookingBridge]
) -> None:
    setattr(app_state, _BRIDGE, factory)


def booking_bridge_for(request: Request, db: AsyncSession) -> BookingBridge:
    factory: Callable[[AsyncSession], BookingBridge] | None = getattr(
        request.app.state, _BRIDGE, None
    )
    if factory is None:
        return NoopBookingBridge()
    return factory(db)


class BlockChecker(Protocol):
    """BR-SAFE-05: blocks are unilateral and silent; both directions hide the pair from each other.

    Owned by ``safety`` (Phase 8); consumed by ``bookings``, ``search`` and ``chat`` through
    this port so the lower modules never import the higher one.
    """

    async def is_blocked_either_way(self, db: AsyncSession, a: UUID, b: UUID) -> bool: ...

    async def hidden_user_ids(self, db: AsyncSession, viewer_id: UUID) -> frozenset[UUID]:
        """Users the viewer blocked plus users who blocked the viewer."""
        ...


class NoopBlockChecker:
    async def is_blocked_either_way(self, db: AsyncSession, a: UUID, b: UUID) -> bool:
        del db, a, b
        return False

    async def hidden_user_ids(self, db: AsyncSession, viewer_id: UUID) -> frozenset[UUID]:
        del db, viewer_id
        return frozenset()


_BLOCKS = "block_checker"


def bind_block_checker(app_state: object, checker: BlockChecker) -> None:
    setattr(app_state, _BLOCKS, checker)


def get_block_checker(request: Request) -> BlockChecker:
    checker = getattr(request.app.state, _BLOCKS, None)
    if checker is None:
        return NoopBlockChecker()
    return checker  # type: ignore[no-any-return]
