"""Bookings FastAPI wiring and the ports other modules call."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.events import EventDispatcher, EventPublisher, event_publisher_for
from app.core.lifecycle import get_block_checker
from app.modules.bookings.repository import BookingRepository
from app.modules.bookings.service import BookingService


def get_booking_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BookingService:
    return BookingService(
        BookingRepository(db),
        settings,
        events=event_publisher_for(request, db),
        blocks=get_block_checker(request),
    )


BookingServiceDep = Annotated[BookingService, Depends(get_booking_service)]


def booking_service_for(
    db: AsyncSession,
    settings: Settings,
    *,
    dispatcher: EventDispatcher | None = None,
) -> BookingService:
    return BookingService(
        BookingRepository(db),
        settings,
        events=EventPublisher(dispatcher, db),
    )


class BookingDeletionGuard:
    """BR-ACC-07: an accepted seat blocks account deletion."""

    async def blockers(self, db: AsyncSession, user_id: UUID) -> tuple[str, ...]:
        count = await BookingRepository(db).count_accepted(user_id)
        if count == 0:
            return ()
        return (f"{count} accepted join request(s)",)


class BookingCancellationStats:
    async def count_recent(self, db: AsyncSession, user_id: UUID, *, days: int) -> int:
        return await BookingRepository(db).count_recent_cancellations(user_id, days=days)
