"""``GET /search/trips`` (api.md §4.6, FR-SRCH-*)."""

from __future__ import annotations

from datetime import date, time
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission
from app.core.authz.principal import Principal
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.lifecycle import BlockChecker, get_block_checker
from app.core.rate_limit import RateLimit, RateLimiter, get_rate_limiter
from app.core.security import keyed_hash
from app.modules.search.dependencies import SearchServiceDep
from app.modules.search.schemas import SearchTripListResponse
from app.modules.vehicles.models import VehicleType

router = APIRouter(prefix="/search", tags=["search"])

_HASH_PREFIX = "search-trips:"


@router.get(
    "/trips",
    response_model=SearchTripListResponse,
    operation_id="search_trips",
    summary="Find published trips compatible with a pickup and drop-off",
)
async def search_trips(
    principal: Annotated[Principal, Depends(require_permission(Permission.SEARCH_TRIPS))],
    service: SearchServiceDep,
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    blocks: Annotated[BlockChecker, Depends(get_block_checker)],
    pickup_lat: Annotated[float, Query(ge=-90, le=90, alias="pickupLat")],
    pickup_lng: Annotated[float, Query(ge=-180, le=180, alias="pickupLng")],
    dropoff_lat: Annotated[float, Query(ge=-90, le=90, alias="dropoffLat")],
    dropoff_lng: Annotated[float, Query(ge=-180, le=180, alias="dropoffLng")],
    day: Annotated[date, Query(alias="date")],
    clock: Annotated[time | None, Query(alias="time")] = None,
    time_from: Annotated[time | None, Query(alias="timeFrom")] = None,
    time_to: Annotated[time | None, Query(alias="timeTo")] = None,
    seats: Annotated[int, Query(ge=1, le=20)] = 1,
    verified_only: Annotated[bool, Query(alias="verifiedOnly")] = False,
    min_rating: Annotated[float | None, Query(ge=1, le=5, alias="minRating")] = None,
    vehicle_type: Annotated[VehicleType | None, Query(alias="vehicleType")] = None,
    price_max: Annotated[int | None, Query(ge=0, alias="priceMax")] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchTripListResponse:
    await limiter.enforce(
        RateLimit.parse("search_trips", settings.search_trips_rate_limit),
        keyed_hash(
            f"{_HASH_PREFIX}{principal.user_id}",
            settings.auth_hash_secret.get_secret_value(),
        ),
    )
    hidden = await blocks.hidden_user_ids(db, principal.user_id)
    items, next_cursor = await service.search_trips(
        pickup_lat=pickup_lat,
        pickup_lng=pickup_lng,
        dropoff_lat=dropoff_lat,
        dropoff_lng=dropoff_lng,
        day=day,
        clock=clock,
        time_from=time_from,
        time_to=time_to,
        seats=seats,
        verified_only=verified_only,
        min_rating=min_rating,
        vehicle_type=None if vehicle_type is None else vehicle_type.value,
        price_max_minor=price_max,
        cursor=cursor,
        limit=limit,
        hidden_driver_ids=hidden,
    )
    return SearchTripListResponse(items=items, next_cursor=next_cursor)
