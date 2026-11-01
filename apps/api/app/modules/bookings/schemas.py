"""HTTP shapes for join requests (api.md §4.7)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiModel
from app.modules.bookings.models import JoinCancelledBy, JoinRequestStatus


class JoinPointInput(ApiModel):
    lat: Annotated[float, Field(ge=-90, le=90)]
    lng: Annotated[float, Field(ge=-180, le=180)]
    label: Annotated[str, Field(min_length=1, max_length=200)]

    @field_validator("label", mode="after")
    @classmethod
    def _trim(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            msg = "must not be blank"
            raise ValueError(msg)
        return trimmed


class JoinRequestCreate(ApiModel):
    seats_requested: Annotated[int, Field(ge=1, le=20)]
    pickup: JoinPointInput
    dropoff: JoinPointInput
    note: Annotated[str, Field(max_length=300)] | None = None


class JoinRequestResponse(ApiModel):
    id: UUID
    trip_id: UUID
    passenger_id: UUID
    status: JoinRequestStatus
    seats_requested: int
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float
    pickup_label: str
    dropoff_label: str
    pickup_fraction: float
    dropoff_fraction: float
    note: str | None
    created_at: datetime
    responded_at: datetime | None
    cancelled_at: datetime | None
    cancelled_by: JoinCancelledBy | None
    minutes_before_departure_at_cancel: int | None
    passenger_display_name: str
    passenger_identity_verified: bool
    passenger_cancellations_last_90_days: int


class JoinRequestListResponse(ApiModel):
    items: list[JoinRequestResponse]
    next_cursor: str | None


class CallContactResponse(ApiModel):
    user_id: UUID
    display_name: str
    phone: str


class CallContactListResponse(ApiModel):
    items: list[CallContactResponse]
