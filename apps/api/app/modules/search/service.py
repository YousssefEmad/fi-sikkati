"""Time-window parsing and ranking assembly for search (BR-MATCH-01..06)."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.core.errors import ValidationAppError
from app.modules.pricing.schemas import SUGGESTED_LABEL
from app.modules.search.schemas import MatchKind, SearchDriverCard, SearchTripItem
from app.modules.trips.repository import MatchCursor, PublishedMatch, TripRepository

CAIRO = ZoneInfo("Africa/Cairo")


@dataclass(frozen=True, slots=True)
class SearchWindow:
    start: datetime
    end: datetime
    requested_at: datetime


def resolve_window(
    *,
    day: date,
    clock: time | None,
    time_from: time | None,
    time_to: time | None,
    default_window_minutes: int,
) -> SearchWindow:
    """Interpret search times in Africa/Cairo (platform default timezone)."""
    if (time_from is None) ^ (time_to is None):
        raise ValidationAppError("timeFrom and timeTo must be sent together.")
    if time_from is not None and time_to is not None:
        start = datetime.combine(day, time_from, tzinfo=CAIRO).astimezone(UTC)
        end = datetime.combine(day, time_to, tzinfo=CAIRO).astimezone(UTC)
        if end <= start:
            raise ValidationAppError("timeTo must be after timeFrom.")
        midpoint = start + (end - start) / 2
        return SearchWindow(start=start, end=end, requested_at=midpoint)
    if clock is not None:
        center = datetime.combine(day, clock, tzinfo=CAIRO).astimezone(UTC)
        delta = timedelta(minutes=default_window_minutes)
        return SearchWindow(start=center - delta, end=center + delta, requested_at=center)
    start_local = datetime.combine(day, time(0, 0), tzinfo=CAIRO)
    end_local = datetime.combine(day + timedelta(days=1), time(0, 0), tzinfo=CAIRO)
    start = start_local.astimezone(UTC)
    end = end_local.astimezone(UTC) - timedelta(microseconds=1)
    noon = datetime.combine(day, time(12, 0), tzinfo=CAIRO).astimezone(UTC)
    return SearchWindow(start=start, end=end, requested_at=noon)


def encode_cursor(match: PublishedMatch) -> str:
    payload = {
        "e": 1 if match.exact_match else 0,
        "d": match.pickup_distance_m + match.dropoff_distance_m,
        "t": match.time_diff_s,
        "s": match.available_seats,
        "dep": match.departure_at.isoformat(),
        "id": str(match.trip_id),
    }
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()


def decode_cursor(value: str | None) -> MatchCursor | None:
    if not value:
        return None
    try:
        raw = json.loads(base64.urlsafe_b64decode(value.encode()).decode())
        return MatchCursor(
            exact=int(raw["e"]),
            distance_sum_m=int(raw["d"]),
            time_diff_s=int(raw["t"]),
            available_seats=int(raw["s"]),
            departure_at=datetime.fromisoformat(raw["dep"]),
            trip_id=UUID(raw["id"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise ValidationAppError("Invalid cursor.") from None


class SearchService:
    def __init__(self, repository: TripRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    async def search_trips(
        self,
        *,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        day: date,
        clock: time | None,
        time_from: time | None,
        time_to: time | None,
        seats: int,
        verified_only: bool,
        min_rating: float | None,
        vehicle_type: str | None,
        price_max_minor: int | None,
        cursor: str | None,
        limit: int,
        hidden_driver_ids: frozenset[UUID] | None = None,
    ) -> tuple[list[SearchTripItem], str | None]:
        window = resolve_window(
            day=day,
            clock=clock,
            time_from=time_from,
            time_to=time_to,
            default_window_minutes=self._settings.matching_default_time_window_minutes,
        )
        rows = await self._repository.search_published(
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng,
            window_from=window.start,
            window_to=window.end,
            requested_at=window.requested_at,
            seats=seats,
            stop_proximity_m=self._settings.matching_stop_proximity_meters,
            verified_only=verified_only,
            vehicle_type=vehicle_type,
            price_max_minor=price_max_minor,
            cursor=decode_cursor(cursor),
            limit=limit + 1,
            hidden_driver_ids=hidden_driver_ids,
            min_rating=min_rating,
            rating_min_count=self._settings.ratings_min_count_to_display,
        )
        page = rows[:limit]
        next_cursor = encode_cursor(page[-1]) if len(rows) > limit else None
        return [_item(row) for row in page], next_cursor


def _item(row: PublishedMatch) -> SearchTripItem:
    return SearchTripItem(
        trip_id=row.trip_id,
        match_kind=MatchKind.EXACT if row.exact_match else MatchKind.ON_ROUTE,
        pickup_distance_m=row.pickup_distance_m,
        dropoff_distance_m=row.dropoff_distance_m,
        departure_at=row.departure_at,
        estimated_arrival_at=row.estimated_arrival_at,
        origin_label=row.origin_label,
        destination_label=row.destination_label,
        origin_lat=row.origin_lat,
        origin_lng=row.origin_lng,
        destination_lat=row.destination_lat,
        destination_lng=row.destination_lng,
        total_seats=row.total_seats,
        available_seats=row.available_seats,
        price_per_seat_minor=row.price_per_seat_minor,
        currency=row.currency,
        price_label=SUGGESTED_LABEL,
        vehicle_type=row.vehicle_type,
        driver=SearchDriverCard(
            user_id=row.driver_id,
            display_name=row.driver_display_name,
            identity_verified=row.identity_verified,
        ),
    )
