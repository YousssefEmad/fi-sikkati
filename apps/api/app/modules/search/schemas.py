"""HTTP shapes for ``GET /search/trips``."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.core.schemas import ApiModel


class MatchKind(StrEnum):
    EXACT = "EXACT"
    ON_ROUTE = "ON_ROUTE"


class SearchDriverCard(ApiModel):
    user_id: UUID
    display_name: str
    identity_verified: bool


class SearchTripItem(ApiModel):
    trip_id: UUID
    match_kind: MatchKind
    pickup_distance_m: int
    dropoff_distance_m: int
    departure_at: datetime
    estimated_arrival_at: datetime
    origin_label: str
    destination_label: str
    origin_lat: float
    origin_lng: float
    destination_lat: float
    destination_lng: float
    total_seats: int
    available_seats: int
    price_per_seat_minor: int | None
    currency: str
    price_label: str
    vehicle_type: str
    driver: SearchDriverCard


class SearchTripListResponse(ApiModel):
    items: list[SearchTripItem]
    next_cursor: str | None
