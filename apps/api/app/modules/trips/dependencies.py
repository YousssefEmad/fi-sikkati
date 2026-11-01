"""Trips FastAPI wiring."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.events import event_publisher_for
from app.core.lifecycle import DeletionGuard, booking_bridge_for
from app.modules.maps.dependencies import MapProviderDep
from app.modules.pricing.dependencies import PricingServiceDep
from app.modules.trips.repository import TripRepository
from app.modules.trips.service import TripService


def get_trip_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    maps: MapProviderDep,
    pricing: PricingServiceDep,
) -> TripService:
    return TripService(
        TripRepository(db),
        maps,
        pricing,
        settings,
        bridge=booking_bridge_for(request, db),
        events=event_publisher_for(request, db),
    )


TripServiceDep = Annotated[TripService, Depends(get_trip_service)]


class TripDeletionGuard:
    """BR-ACC-07: block account close while a trip is still live."""

    async def blockers(self, db: AsyncSession, user_id: UUID) -> tuple[str, ...]:
        count = await TripRepository(db).count_blocking_deletion(user_id)
        if count == 0:
            return ()
        return (f"{count} active trip(s)",)


def trip_deletion_guard() -> DeletionGuard:
    return TripDeletionGuard()
