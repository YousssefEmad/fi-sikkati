"""HTTP shapes for trips."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiModel
from app.modules.trips.models import StopKind, TripStatus


class TripStopInput(ApiModel):
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


class TripCreateRequest(ApiModel):
    vehicle_id: UUID
    departure_at: datetime
    total_seats: Annotated[int, Field(ge=1, le=20)]
    stops: Annotated[list[TripStopInput], Field(min_length=2, max_length=8)]
    notes: Annotated[str, Field(max_length=500)] | None = None


class TripUpdateRequest(ApiModel):
    vehicle_id: UUID | None = None
    departure_at: datetime | None = None
    total_seats: Annotated[int, Field(ge=1, le=20)] | None = None
    stops: Annotated[list[TripStopInput], Field(min_length=2, max_length=8)] | None = None
    notes: Annotated[str, Field(max_length=500)] | None = None


class TripCancelRequest(ApiModel):
    reason: Annotated[str, Field(min_length=0, max_length=500)] | None = None


class TripStopResponse(ApiModel):
    sequence: int
    kind: StopKind
    label: str
    lat: float
    lng: float
    route_fraction: float


class TripResponse(ApiModel):
    id: UUID
    driver_id: UUID
    vehicle_id: UUID
    status: TripStatus
    departure_at: datetime
    estimated_arrival_at: datetime
    total_seats: int
    available_seats: int
    origin_label: str
    destination_label: str
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    notes: str | None
    version: int
    distance_m: int | None
    duration_s: int | None
    price_per_seat_minor: int | None
    currency: str
    price_label: str
    stops: list[TripStopResponse]
    route_coordinates: list[list[float]]
    exact_stops: bool


class TripListResponse(ApiModel):
    items: list[TripResponse]
    next_cursor: str | None
