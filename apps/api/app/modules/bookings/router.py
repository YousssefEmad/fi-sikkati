"""``/join-requests`` (api.md §4.7)."""

from __future__ import annotations

import base64
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission
from app.core.authz.principal import Principal
from app.core.errors import ValidationAppError
from app.modules.bookings.dependencies import BookingServiceDep
from app.modules.bookings.models import JoinRequestStatus
from app.modules.bookings.schemas import (
    CallContactListResponse,
    CallContactResponse,
    JoinRequestCreate,
    JoinRequestListResponse,
    JoinRequestResponse,
)
from app.modules.bookings.service import JoinPoint, JoinView

trip_join_router = APIRouter(prefix="/trips", tags=["bookings"])
join_router = APIRouter(prefix="/join-requests", tags=["bookings"])
me_join_router = APIRouter(prefix="/me/join-requests", tags=["bookings"])


def _response(view: JoinView) -> JoinRequestResponse:
    return JoinRequestResponse(
        id=view.id,
        trip_id=view.trip_id,
        passenger_id=view.passenger_id,
        status=view.status,
        seats_requested=view.seats_requested,
        pickup_lat=view.pickup_lat,
        pickup_lng=view.pickup_lng,
        dropoff_lat=view.dropoff_lat,
        dropoff_lng=view.dropoff_lng,
        pickup_label=view.pickup_label,
        dropoff_label=view.dropoff_label,
        pickup_fraction=view.pickup_fraction,
        dropoff_fraction=view.dropoff_fraction,
        note=view.note,
        created_at=view.created_at,
        responded_at=view.responded_at,
        cancelled_at=view.cancelled_at,
        cancelled_by=view.cancelled_by,
        minutes_before_departure_at_cancel=view.minutes_before_departure_at_cancel,
        passenger_display_name=view.passenger_display_name,
        passenger_identity_verified=view.passenger_identity_verified,
        passenger_cancellations_last_90_days=view.passenger_cancellations_last_90_days,
    )


def _encode_cursor(created_at: datetime, request_id: UUID) -> str:
    raw = f"{created_at.isoformat()}|{request_id}"
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


def _statuses(value: str | None) -> frozenset[JoinRequestStatus] | None:
    if not value:
        return None
    try:
        return frozenset(JoinRequestStatus(part) for part in value.split(",") if part)
    except ValueError as exc:
        raise ValidationAppError("Unknown request status.") from exc


def _page(rows: list[JoinView], *, limit: int) -> JoinRequestListResponse:
    page = rows[:limit]
    cursor = None
    if len(rows) > limit and page:
        last = page[-1]
        cursor = _encode_cursor(last.created_at, last.id)
    return JoinRequestListResponse(items=[_response(item) for item in page], next_cursor=cursor)


@trip_join_router.post(
    "/{trip_id}/join-requests",
    response_model=JoinRequestResponse,
    operation_id="join_requests_create",
    summary="Request a seat on a published trip",
)
async def create_join_request(
    trip_id: UUID,
    payload: JoinRequestCreate,
    service: BookingServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.JOIN_REQUESTS_CREATE))],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> JoinRequestResponse:
    view = await service.create(
        passenger_id=principal.user_id,
        roles=principal.roles,
        email_verified=principal.email_verified,
        phone_verified=principal.phone_verified,
        trip_id=trip_id,
        seats_requested=payload.seats_requested,
        pickup=JoinPoint(
            lat=payload.pickup.lat, lng=payload.pickup.lng, label=payload.pickup.label
        ),
        dropoff=JoinPoint(
            lat=payload.dropoff.lat, lng=payload.dropoff.lng, label=payload.dropoff.label
        ),
        note=payload.note,
        idempotency_key=idempotency_key,
    )
    return _response(view)


@trip_join_router.get(
    "/{trip_id}/join-requests",
    response_model=JoinRequestListResponse,
    operation_id="join_requests_list_for_trip",
    summary="List join requests for a trip the caller drives",
)
async def list_for_trip(
    trip_id: UUID,
    service: BookingServiceDep,
    principal: Annotated[
        Principal, Depends(require_permission(Permission.JOIN_REQUESTS_LIST_FOR_TRIP))
    ],
    status: Annotated[str | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> JoinRequestListResponse:
    rows = await service.list_for_trip(
        trip_id,
        viewer_id=principal.user_id,
        is_admin=principal.is_admin,
        statuses=_statuses(status),
        before=_decode_cursor(cursor),
        limit=limit + 1,
    )
    return _page(rows, limit=limit)


@me_join_router.get(
    "",
    response_model=JoinRequestListResponse,
    operation_id="join_requests_list_mine",
    summary="List the signed-in passenger's join requests",
)
async def list_mine(
    service: BookingServiceDep,
    principal: Annotated[
        Principal, Depends(require_permission(Permission.JOIN_REQUESTS_LIST_MINE))
    ],
    status: Annotated[str | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> JoinRequestListResponse:
    rows = await service.list_mine(
        principal.user_id,
        statuses=_statuses(status),
        before=_decode_cursor(cursor),
        limit=limit + 1,
    )
    return _page(rows, limit=limit)


@join_router.get(
    "/{request_id}",
    response_model=JoinRequestResponse,
    operation_id="join_requests_get",
    summary="Read one join request",
)
async def get_join_request(
    request_id: UUID,
    service: BookingServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.JOIN_REQUESTS_READ))],
) -> JoinRequestResponse:
    view = await service.get(request_id, viewer_id=principal.user_id, is_admin=principal.is_admin)
    return _response(view)


@join_router.post(
    "/{request_id}/accept",
    response_model=JoinRequestResponse,
    operation_id="join_requests_accept",
    summary="Accept a pending request and reserve the seats",
)
async def accept_join_request(
    request_id: UUID,
    service: BookingServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.JOIN_REQUESTS_ACCEPT))],
) -> JoinRequestResponse:
    return _response(await service.accept(request_id, driver_id=principal.user_id))


@join_router.post(
    "/{request_id}/reject",
    response_model=JoinRequestResponse,
    operation_id="join_requests_reject",
    summary="Reject a pending request",
)
async def reject_join_request(
    request_id: UUID,
    service: BookingServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.JOIN_REQUESTS_REJECT))],
) -> JoinRequestResponse:
    return _response(await service.reject(request_id, driver_id=principal.user_id))


@join_router.post(
    "/{request_id}/cancel",
    response_model=JoinRequestResponse,
    operation_id="join_requests_cancel",
    summary="Cancel the caller's own request",
)
async def cancel_join_request(
    request_id: UUID,
    service: BookingServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.JOIN_REQUESTS_CANCEL))],
) -> JoinRequestResponse:
    return _response(await service.cancel(request_id, passenger_id=principal.user_id))


@trip_join_router.get(
    "/{trip_id}/call-contacts",
    response_model=CallContactListResponse,
    operation_id="trip_call_contacts",
    summary="Phone numbers of the other people on an accepted trip",
)
async def trip_call_contacts(
    trip_id: UUID,
    service: BookingServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.TRIPS_READ))],
) -> CallContactListResponse:
    contacts = await service.call_contacts(trip_id, principal.user_id)
    return CallContactListResponse(
        items=[
            CallContactResponse(
                user_id=item.user_id, display_name=item.display_name, phone=item.phone
            )
            for item in contacts
        ]
    )
