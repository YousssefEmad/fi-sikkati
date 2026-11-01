"""``/trips`` and ``/me/trips`` (api.md §4.5)."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission
from app.core.authz.principal import Principal
from app.modules.pricing.schemas import SUGGESTED_LABEL
from app.modules.trips.dependencies import TripServiceDep
from app.modules.trips.models import TripStatus
from app.modules.trips.schemas import (
    TripCancelRequest,
    TripCreateRequest,
    TripListResponse,
    TripResponse,
    TripStopResponse,
    TripUpdateRequest,
)
from app.modules.trips.service import StopInput, StopView, TripView

trips_router = APIRouter(prefix="/trips", tags=["trips"])
me_trips_router = APIRouter(prefix="/me/trips", tags=["trips"])


def _stop(item: StopView) -> TripStopResponse:
    return TripStopResponse(
        sequence=item.sequence,
        kind=item.kind,
        label=item.label,
        lat=item.lat,
        lng=item.lng,
        route_fraction=item.route_fraction,
    )


def _response(view: TripView) -> TripResponse:
    return TripResponse(
        id=view.id,
        driver_id=view.driver_id,
        vehicle_id=view.vehicle_id,
        status=view.status,
        departure_at=view.departure_at,
        estimated_arrival_at=view.estimated_arrival_at,
        total_seats=view.total_seats,
        available_seats=view.available_seats,
        origin_label=view.origin_label,
        destination_label=view.destination_label,
        origin_lat=view.origin_lat,
        origin_lng=view.origin_lng,
        destination_lat=view.destination_lat,
        destination_lng=view.destination_lng,
        notes=view.notes,
        version=view.version,
        distance_m=view.distance_m,
        duration_s=view.duration_s,
        price_per_seat_minor=view.price_per_seat_minor,
        currency=view.currency,
        price_label=SUGGESTED_LABEL,
        stops=[_stop(item) for item in view.stops],
        route_coordinates=[list(pair) for pair in view.route_coordinates],
        exact_stops=view.exact_stops,
    )


def _stops(payload: list[object]) -> tuple[StopInput, ...]:
    return tuple(
        StopInput(lat=item.lat, lng=item.lng, label=item.label)  # type: ignore[attr-defined]
        for item in payload
    )


def _encode_cursor(departure_at: datetime, trip_id: UUID) -> str:
    raw = f"{departure_at.isoformat()}|{trip_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(value: str | None) -> tuple[datetime, UUID] | None:
    if not value:
        return None
    try:
        decoded = base64.urlsafe_b64decode(value.encode()).decode()
        stamp, _, ident = decoded.partition("|")
        return datetime.fromisoformat(stamp), UUID(ident)
    except (ValueError, UnicodeError):
        return None


@trips_router.post(
    "",
    response_model=TripResponse,
    operation_id="trips_create",
    summary="Create a draft trip",
)
async def create_trip(
    payload: TripCreateRequest,
    service: TripServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.TRIPS_CREATE))],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> TripResponse:
    view = await service.create(
        driver_id=principal.user_id,
        email_verified=principal.email_verified,
        phone_verified=principal.phone_verified,
        vehicle_id=payload.vehicle_id,
        departure_at=payload.departure_at,
        total_seats=payload.total_seats,
        stops=_stops(list(payload.stops)),
        notes=payload.notes,
        idempotency_key=idempotency_key,
    )
    return _response(view)


@trips_router.get(
    "/{trip_id}",
    response_model=TripResponse,
    operation_id="trips_get",
    summary="Trip detail (privacy-filtered)",
)
async def get_trip(
    trip_id: UUID,
    service: TripServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.TRIPS_READ))],
) -> TripResponse:
    view = await service.get(trip_id, viewer_id=principal.user_id, is_admin=principal.is_admin)
    return _response(view)


@trips_router.patch(
    "/{trip_id}",
    response_model=TripResponse,
    operation_id="trips_update",
    summary="Edit a trip",
)
async def update_trip(
    trip_id: UUID,
    payload: TripUpdateRequest,
    service: TripServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.TRIPS_UPDATE))],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> TripResponse:
    version = int(if_match) if if_match and if_match.isdigit() else None
    view = await service.update(
        trip_id,
        driver_id=principal.user_id,
        expected_version=version,
        vehicle_id=payload.vehicle_id,
        departure_at=payload.departure_at,
        total_seats=payload.total_seats,
        stops=None if payload.stops is None else _stops(list(payload.stops)),
        notes=payload.notes,
    )
    return _response(view)


@trips_router.post(
    "/{trip_id}/publish",
    response_model=TripResponse,
    operation_id="trips_publish",
    summary="Publish a draft",
)
async def publish_trip(
    trip_id: UUID,
    service: TripServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.TRIPS_PUBLISH))],
) -> TripResponse:
    return _response(await service.publish(trip_id, driver_id=principal.user_id))


@trips_router.post(
    "/{trip_id}/start",
    response_model=TripResponse,
    operation_id="trips_start",
    summary="Mark the trip in progress",
)
async def start_trip(
    trip_id: UUID,
    service: TripServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.TRIPS_START))],
) -> TripResponse:
    return _response(await service.start(trip_id, driver_id=principal.user_id))


@trips_router.post(
    "/{trip_id}/complete",
    response_model=TripResponse,
    operation_id="trips_complete",
    summary="Complete the trip",
)
async def complete_trip(
    trip_id: UUID,
    service: TripServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.TRIPS_COMPLETE))],
) -> TripResponse:
    return _response(await service.complete(trip_id, driver_id=principal.user_id))


@trips_router.post(
    "/{trip_id}/cancel",
    response_model=TripResponse,
    operation_id="trips_cancel",
    summary="Cancel the trip",
)
async def cancel_trip(
    trip_id: UUID,
    service: TripServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.TRIPS_CANCEL))],
    payload: TripCancelRequest | None = None,
) -> TripResponse:
    return _response(
        await service.cancel(
            trip_id,
            actor_id=principal.user_id,
            as_admin=principal.is_admin,
            reason=None if payload is None else payload.reason,
        )
    )


@me_trips_router.get(
    "",
    response_model=TripListResponse,
    operation_id="trips_list_mine",
    summary="The signed-in user's trips",
)
async def list_mine(
    service: TripServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.TRIPS_LIST_OWN))],
    response: Response,
    role: Annotated[str, Query()] = "driver",
    status: Annotated[str | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> TripListResponse:
    del response
    statuses = None
    if status:
        statuses = frozenset({TripStatus(part) for part in status.split(",") if part})
    decoded = _decode_cursor(cursor)
    if role == "passenger":
        items = await service.list_as_passenger(
            principal.user_id, statuses=statuses, cursor=decoded, limit=limit + 1
        )
    elif role == "driver":
        items = await service.list_mine(
            principal.user_id, statuses=statuses, cursor=decoded, limit=limit + 1
        )
    else:
        return TripListResponse(items=[], next_cursor=None)
    next_cursor = None
    page = items[:limit]
    if len(items) > limit:
        last = page[-1]
        next_cursor = _encode_cursor(last.departure_at, last.id)
    return TripListResponse(items=[_response(item) for item in page], next_cursor=next_cursor)
