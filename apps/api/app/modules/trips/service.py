"""Trip lifecycle rules (BR-TRIP-01…11, OD-017/023)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from app.core.config import Settings
from app.core.errors import (
    ConflictError,
    EmailNotVerifiedError,
    ForbiddenError,
    IdempotencyConflictError,
    InvalidTransitionError,
    NotFoundError,
    OverlappingTripError,
    PreconditionRequiredError,
    VehicleNotEligibleError,
    VersionConflictError,
)
from app.core.events import (
    EventPublisher,
    NoopEventPublisher,
    TripCancelled,
    TripCompleted,
    TripPublished,
    TripStarted,
    TripUpdated,
)
from app.core.ids import uuid7
from app.core.lifecycle import BookingBridge
from app.modules.maps.ports import GeoPoint, MapProvider, RouteResult
from app.modules.pricing.models import CURRENCY_EGP
from app.modules.pricing.service import PricingService
from app.modules.trips.models import (
    ACTIVE_TRIP_STATUSES,
    CancelledBy,
    StopKind,
    Trip,
    TripStatus,
)
from app.modules.trips.repository import TripRepository
from app.modules.vehicles.models import Vehicle

EDITABLE_STATUSES = frozenset({TripStatus.DRAFT, TripStatus.PUBLISHED, TripStatus.FULL})
MAX_NOTES = 500
MAX_WAYPOINTS = 6
MIN_STOPS = 2
ADMIN_CANCEL_REASON_MIN = 3


@dataclass(frozen=True, slots=True)
class StopInput:
    lat: float
    lng: float
    label: str


@dataclass(frozen=True, slots=True)
class StopView:
    sequence: int
    kind: StopKind
    label: str
    lat: float
    lng: float
    route_fraction: float


@dataclass(frozen=True, slots=True)
class TripView:
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
    stops: tuple[StopView, ...]
    route_coordinates: tuple[tuple[float, float], ...]
    exact_stops: bool


class TripService:
    def __init__(
        self,
        repository: TripRepository,
        maps: MapProvider,
        pricing: PricingService,
        settings: Settings,
        bridge: BookingBridge | None = None,
        events: EventPublisher | None = None,
    ) -> None:
        self._repository = repository
        self._maps = maps
        self._pricing = pricing
        self._settings = settings
        self._bridge = bridge
        self._events = events or NoopEventPublisher()

    async def create(
        self,
        *,
        driver_id: UUID,
        email_verified: bool,
        phone_verified: bool,
        vehicle_id: UUID,
        departure_at: datetime,
        total_seats: int,
        stops: tuple[StopInput, ...],
        notes: str | None,
        idempotency_key: str | None,
        now: datetime | None = None,
    ) -> TripView:
        del phone_verified  # Phone confirmation is optional (OD-004 / BR-ACC-01).
        if not email_verified:
            raise EmailNotVerifiedError("Confirm your email before publishing trips.")
        if idempotency_key:
            existing = await self._repository.get_by_idempotency(driver_id, idempotency_key)
            if existing is not None:
                same = (
                    existing.vehicle_id == vehicle_id
                    and existing.departure_at == departure_at
                    and existing.total_seats == total_seats
                )
                if not same:
                    raise IdempotencyConflictError(
                        "This idempotency key was already used with a different trip."
                    )
                return await self._view(existing, exact=True)
        moment = now or datetime.now(UTC)
        vehicle = await self._require_vehicle(vehicle_id, driver_id)
        self._validate_seats(total_seats, vehicle.seat_capacity)
        geo_stops = self._geo_stops(stops)
        route = await self._maps.route(geo_stops)
        arrival = departure_at + timedelta(seconds=route.duration_s)
        self._ensure_departure_window(departure_at, arrival, moment, publishing=False)
        trip_id = uuid7()
        trip = await self._repository.create(
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            departure_at=departure_at,
            estimated_arrival_at=arrival,
            total_seats=total_seats,
            origin=geo_stops[0],
            destination=geo_stops[-1],
            blur_meters=self._settings.privacy_location_blur_meters,
            trip_id=trip_id,
            notes=_notes(notes),
            idempotency_key=idempotency_key,
            currency=CURRENCY_EGP,
        )
        await self._apply_route(trip, geo_stops, route, moment)
        quote = await self._pricing.quote(route.distance_m, at=moment)
        trip.pricing_rule_id = quote.rule_id
        trip.price_per_seat_minor = quote.passenger_price_minor
        trip.platform_fee_minor = quote.platform_fee_minor
        trip.driver_amount_minor = quote.driver_amount_minor
        loaded = await self._repository.get(trip.id)
        if loaded is None:
            raise NotFoundError("Trip not found.")
        return await self._view(loaded, exact=True)

    async def get(self, trip_id: UUID, *, viewer_id: UUID, is_admin: bool) -> TripView:
        trip = await self._require(trip_id)
        exact = is_admin or trip.driver_id == viewer_id
        if not exact and self._bridge is not None:
            exact = await self._bridge.is_accepted_passenger(trip_id, viewer_id)
        if trip.status is TripStatus.DRAFT and not exact:
            raise NotFoundError("Trip not found.")
        return await self._view(trip, exact=exact)

    async def list_browse(self, *, limit: int = 12) -> list[TripView]:
        """Public-ish home feed of upcoming published trips (approximate stops)."""
        rows = await self._repository.list_upcoming_published(
            limit=limit, now=datetime.now(UTC)
        )
        return [await self._view(row, exact=False) for row in rows]

    async def list_mine(
        self,
        driver_id: UUID,
        *,
        statuses: frozenset[TripStatus] | None,
        cursor: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[TripView]:
        before_departure, before_id = (None, None) if cursor is None else cursor
        rows = await self._repository.list_for_driver(
            driver_id,
            statuses=statuses,
            before_departure=before_departure,
            before_id=before_id,
            limit=limit,
        )
        return [await self._view(row, exact=True) for row in rows]

    async def list_as_passenger(
        self,
        passenger_id: UUID,
        *,
        statuses: frozenset[TripStatus] | None,
        cursor: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[TripView]:
        if self._bridge is None:
            return []
        names = None if statuses is None else frozenset(item.value for item in statuses)
        ids = await self._bridge.list_passenger_trip_ids(
            passenger_id, statuses=names, before=cursor, limit=limit
        )
        rows = await self._repository.get_many(ids)
        return [await self._view(row, exact=True) for row in rows]

    async def update(
        self,
        trip_id: UUID,
        *,
        driver_id: UUID,
        expected_version: int | None,
        vehicle_id: UUID | None,
        departure_at: datetime | None,
        total_seats: int | None,
        stops: tuple[StopInput, ...] | None,
        notes: str | None,
        now: datetime | None = None,
    ) -> TripView:
        trip = await self._require_owned(trip_id, driver_id)
        if trip.status not in EDITABLE_STATUSES:
            raise InvalidTransitionError("This trip can no longer be edited.")
        self._assert_version(trip, expected_version)
        moment = now or datetime.now(UTC)
        has_acceptances = trip.available_seats < trip.total_seats
        if has_acceptances:
            self._restrict_after_acceptances(
                trip, departure_at=departure_at, stops=stops, total_seats=total_seats
            )
        vehicle = await self._assign_vehicle(trip, driver_id, vehicle_id, has_acceptances)
        if total_seats is not None:
            self._apply_seat_change(trip, total_seats, vehicle.seat_capacity)
        if notes is not None:
            trip.notes = _notes(notes)
        next_departure = departure_at or trip.departure_at
        geo_stops = self._geo_stops(stops) if stops is not None else None
        if geo_stops is not None:
            await self._reprice_with_stops(trip, geo_stops, next_departure, moment)
        elif departure_at is not None:
            duration = trip.estimated_arrival_at - trip.departure_at
            trip.estimated_arrival_at = departure_at + duration
        if departure_at is not None:
            trip.departure_at = departure_at
        if trip.status in ACTIVE_TRIP_STATUSES:
            await self._reject_overlap(
                driver_id, trip.departure_at, trip.estimated_arrival_at, trip.id
            )
        trip.version += 1
        if trip.status in ACTIVE_TRIP_STATUSES:
            await self._events.publish(
                TripUpdated(
                    trip_id=trip.id,
                    driver_id=trip.driver_id,
                    passenger_ids=await self._passenger_ids(trip.id),
                )
            )
        loaded = await self._repository.get(trip.id)
        if loaded is None:
            raise NotFoundError("Trip not found.")
        return await self._view(loaded, exact=True)

    async def publish(
        self, trip_id: UUID, *, driver_id: UUID, now: datetime | None = None
    ) -> TripView:
        trip = await self._require_owned(trip_id, driver_id)
        if trip.status is not TripStatus.DRAFT:
            raise InvalidTransitionError("Only a draft can be published.")
        moment = now or datetime.now(UTC)
        if trip.departure_at <= moment:
            raise InvalidTransitionError("departureAt must be in the future at publish time.")
        vehicle = await self._require_vehicle(trip.vehicle_id, driver_id)
        self._validate_seats(trip.total_seats, vehicle.seat_capacity)
        if trip.route is None:
            raise InvalidTransitionError("A route is required before publishing.")
        await self._reject_overlap(driver_id, trip.departure_at, trip.estimated_arrival_at, trip.id)
        quote = await self._pricing.quote(trip.route.distance_m, at=moment)
        trip.pricing_rule_id = quote.rule_id
        trip.price_per_seat_minor = quote.passenger_price_minor
        trip.platform_fee_minor = quote.platform_fee_minor
        trip.driver_amount_minor = quote.driver_amount_minor
        trip.status = TripStatus.PUBLISHED
        trip.published_at = moment
        trip.version += 1
        await self._events.publish(TripPublished(trip_id=trip.id, driver_id=trip.driver_id))
        return await self._view(trip, exact=True)

    async def start(
        self, trip_id: UUID, *, driver_id: UUID, now: datetime | None = None
    ) -> TripView:
        trip = await self._require_owned(trip_id, driver_id)
        if trip.status not in {TripStatus.PUBLISHED, TripStatus.FULL}:
            raise InvalidTransitionError("Only a published trip can be started.")
        moment = now or datetime.now(UTC)
        window = timedelta(minutes=self._settings.trips_start_window_minutes)
        if moment < trip.departure_at - window:
            raise InvalidTransitionError("Too early to start this trip.")
        trip.status = TripStatus.IN_PROGRESS
        trip.started_at = moment
        trip.version += 1
        await self._events.publish(
            TripStarted(
                trip_id=trip.id,
                driver_id=trip.driver_id,
                passenger_ids=await self._passenger_ids(trip.id),
            )
        )
        return await self._view(trip, exact=True)

    async def complete(
        self, trip_id: UUID, *, driver_id: UUID, now: datetime | None = None
    ) -> TripView:
        trip = await self._repository.lock(trip_id)
        if trip is None or trip.driver_id != driver_id:
            raise NotFoundError("Trip not found.")
        if trip.status is not TripStatus.IN_PROGRESS:
            raise InvalidTransitionError("Only an in-progress trip can be completed.")
        trip.status = TripStatus.COMPLETED
        trip.completed_at = now or datetime.now(UTC)
        trip.version += 1
        passengers = await self._passenger_ids(trip.id)
        if self._bridge is not None:
            await self._bridge.on_trip_completed(trip.id, now=trip.completed_at)
        await self._events.publish(
            TripCompleted(trip_id=trip.id, driver_id=trip.driver_id, passenger_ids=passengers)
        )
        return await self._view(trip, exact=True)

    async def cancel(
        self,
        trip_id: UUID,
        *,
        actor_id: UUID,
        as_admin: bool,
        reason: str | None,
        now: datetime | None = None,
    ) -> TripView:
        trip = await self._repository.lock(trip_id)
        if trip is None:
            raise NotFoundError("Trip not found.")
        is_owner = trip.driver_id == actor_id
        if not is_owner and not as_admin:
            raise ForbiddenError("You cannot cancel this trip.")
        admin_cancel = as_admin and not is_owner
        if trip.status in {TripStatus.COMPLETED, TripStatus.CANCELLED, TripStatus.EXPIRED}:
            raise InvalidTransitionError("This trip is already finished.")
        if admin_cancel and (reason is None or len(reason.strip()) < ADMIN_CANCEL_REASON_MIN):
            raise InvalidTransitionError("A reason is required when an administrator cancels.")
        trip.status = TripStatus.CANCELLED
        trip.cancelled_at = now or datetime.now(UTC)
        trip.cancelled_by = CancelledBy.ADMIN if admin_cancel else CancelledBy.DRIVER
        trip.cancel_reason = None if reason is None else reason.strip()[:500]
        trip.version += 1
        actor = "ADMIN" if admin_cancel else "DRIVER"
        passengers = await self._passenger_ids(trip.id, include_pending=True)
        if self._bridge is not None and trip.cancelled_at is not None:
            await self._bridge.on_trip_cancelled(trip.id, cancelled_by=actor, now=trip.cancelled_at)
        await self._events.publish(
            TripCancelled(
                trip_id=trip.id,
                driver_id=trip.driver_id,
                passenger_ids=passengers,
                cancelled_by=actor,
                reason=trip.cancel_reason,
            )
        )
        return await self._view(trip, exact=True)

    async def expire_due(self, now: datetime | None = None) -> int:
        moment = now or datetime.now(UTC)
        cutoff = moment - timedelta(minutes=self._settings.trips_expire_grace_minutes)
        count = 0
        for trip in await self._repository.list_due_to_expire(cutoff):
            trip.status = TripStatus.EXPIRED
            trip.expired_at = moment
            trip.version += 1
            count += 1
        return count

    async def auto_complete_due(self, now: datetime | None = None) -> int:
        moment = now or datetime.now(UTC)
        cutoff = moment - timedelta(hours=self._settings.trips_auto_complete_hours)
        count = 0
        for trip in await self._repository.list_due_to_complete(cutoff):
            trip.status = TripStatus.COMPLETED
            trip.completed_at = moment
            trip.version += 1
            passengers = await self._passenger_ids(trip.id)
            if self._bridge is not None:
                await self._bridge.on_trip_completed(trip.id, now=moment)
            await self._events.publish(
                TripCompleted(trip_id=trip.id, driver_id=trip.driver_id, passenger_ids=passengers)
            )
            count += 1
        return count

    async def purge_yesterdays_finished(self, now: datetime | None = None) -> int:
        """Drop finished trips from before today's Cairo midnight, with their trip chat."""
        if not self._settings.trips_daily_purge_enabled:
            return 0
        moment = now or datetime.now(UTC)
        cairo = ZoneInfo("Africa/Cairo")
        local = moment.astimezone(cairo)
        start_of_today = datetime(local.year, local.month, local.day, tzinfo=cairo).astimezone(UTC)
        return await self._repository.purge_finished_before(start_of_today)

    async def _passenger_ids(
        self, trip_id: UUID, *, include_pending: bool = False
    ) -> tuple[UUID, ...]:
        if self._bridge is None:
            return ()
        return await self._bridge.passenger_ids(trip_id, include_pending=include_pending)

    async def deletion_blockers(self, user_id: UUID) -> tuple[str, ...]:
        count = await self._repository.count_blocking_deletion(user_id)
        if count == 0:
            return ()
        return (f"{count} active trip(s)",)

    async def _apply_route(
        self, trip: Trip, stops: tuple[GeoPoint, ...], route: RouteResult, moment: datetime
    ) -> None:
        n = len(stops)
        labelled: list[tuple[int, StopKind, GeoPoint, float]] = []
        for index, stop in enumerate(stops):
            if index == 0:
                kind = StopKind.ORIGIN
            elif index == n - 1:
                kind = StopKind.DESTINATION
            else:
                kind = StopKind.WAYPOINT
            fraction = 0.0 if n == 1 else index / (n - 1)
            labelled.append((index, kind, stop, fraction))
        await self._repository.replace_stops(trip, tuple(labelled))
        await self._repository.upsert_route(
            trip,
            route,
            corridor_meters=self._settings.matching_corridor_width_meters,
            computed_at=moment,
        )

    async def _view(self, trip: Trip, *, exact: bool) -> TripView:
        origin_lat, origin_lng = await self._repository.point_lat_lng(
            trip.origin_point if exact else trip.origin_area_point
        )
        dest_lat, dest_lng = await self._repository.point_lat_lng(
            trip.destination_point if exact else trip.destination_area_point
        )
        stop_views: list[StopView] = []
        if exact:
            for stop in trip.stops:
                lat, lng = await self._repository.point_lat_lng(stop.point)
                stop_views.append(
                    StopView(
                        sequence=stop.sequence,
                        kind=stop.kind,
                        label=stop.label,
                        lat=lat,
                        lng=lng,
                        route_fraction=float(stop.route_fraction),
                    )
                )
        coordinates: tuple[tuple[float, float], ...] = ()
        distance = duration = None
        if trip.route is not None:
            distance = trip.route.distance_m
            duration = trip.route.duration_s
            if exact:
                coordinates = await self._repository.route_coordinates(trip.route)
        return TripView(
            id=trip.id,
            driver_id=trip.driver_id,
            vehicle_id=trip.vehicle_id,
            status=trip.status,
            departure_at=trip.departure_at,
            estimated_arrival_at=trip.estimated_arrival_at,
            total_seats=trip.total_seats,
            available_seats=trip.available_seats,
            origin_label=trip.origin_label,
            destination_label=trip.destination_label,
            origin_lat=origin_lat,
            origin_lng=origin_lng,
            destination_lat=dest_lat,
            destination_lng=dest_lng,
            notes=trip.notes,
            version=trip.version,
            distance_m=distance,
            duration_s=duration,
            price_per_seat_minor=trip.price_per_seat_minor,
            currency=trip.currency,
            stops=tuple(stop_views),
            route_coordinates=coordinates,
            exact_stops=exact,
        )

    async def _require(self, trip_id: UUID) -> Trip:
        trip = await self._repository.get(trip_id)
        if trip is None:
            raise NotFoundError("Trip not found.")
        return trip

    async def _require_owned(self, trip_id: UUID, driver_id: UUID) -> Trip:
        trip = await self._require(trip_id)
        if trip.driver_id != driver_id:
            raise NotFoundError("Trip not found.")
        return trip

    async def _require_vehicle(self, vehicle_id: UUID, owner_id: UUID) -> Vehicle:
        vehicle = await self._repository.get_eligible_vehicle(vehicle_id, owner_id)
        if vehicle is None:
            raise VehicleNotEligibleError(
                "The vehicle must be yours, ACTIVE, and APPROVED (FR-DRV-06)."
            )
        return vehicle

    async def _assign_vehicle(
        self, trip: Trip, driver_id: UUID, vehicle_id: UUID | None, has_acceptances: bool
    ) -> Vehicle:
        if vehicle_id is not None and vehicle_id != trip.vehicle_id:
            if has_acceptances:
                raise InvalidTransitionError("Change the vehicle by cancelling and republishing.")
            vehicle = await self._require_vehicle(vehicle_id, driver_id)
            trip.vehicle_id = vehicle.id
            return vehicle
        return await self._require_vehicle(trip.vehicle_id, driver_id)

    def _apply_seat_change(self, trip: Trip, total_seats: int, seat_capacity: int) -> None:
        reserved = trip.total_seats - trip.available_seats
        if total_seats < reserved:
            raise InvalidTransitionError("totalSeats cannot drop below seats already reserved.")
        self._validate_seats(total_seats, seat_capacity)
        delta = total_seats - trip.total_seats
        trip.total_seats = total_seats
        trip.available_seats += delta

    async def _reprice_with_stops(
        self,
        trip: Trip,
        geo_stops: tuple[GeoPoint, ...],
        departure: datetime,
        moment: datetime,
    ) -> None:
        route = await self._maps.route(geo_stops)
        trip.origin_label = geo_stops[0].label
        trip.destination_label = geo_stops[-1].label
        await self._apply_route(trip, geo_stops, route, moment)
        quote = await self._pricing.quote(route.distance_m, at=moment)
        trip.pricing_rule_id = quote.rule_id
        trip.price_per_seat_minor = quote.passenger_price_minor
        trip.platform_fee_minor = quote.platform_fee_minor
        trip.driver_amount_minor = quote.driver_amount_minor
        trip.estimated_arrival_at = departure + timedelta(seconds=route.duration_s)

    async def _reject_overlap(
        self, driver_id: UUID, departure: datetime, arrival: datetime, exclude_id: UUID
    ) -> None:
        other = await self._repository.overlapping(
            driver_id, departure_at=departure, estimated_arrival_at=arrival, exclude_id=exclude_id
        )
        if other is not None:
            raise OverlappingTripError("You already have a trip in this time window.")

    def _validate_seats(self, total_seats: int, seat_capacity: int) -> None:
        cap = min(seat_capacity - 1, self._settings.trips_max_passenger_seats)
        if total_seats < 1 or total_seats > cap:
            raise InvalidTransitionError(f"Passenger seats must be between 1 and {cap}.")

    def _geo_stops(self, stops: tuple[StopInput, ...]) -> tuple[GeoPoint, ...]:
        if len(stops) < MIN_STOPS:
            raise InvalidTransitionError("A trip needs an origin and a destination.")
        if len(stops) > MIN_STOPS + MAX_WAYPOINTS:
            raise InvalidTransitionError("Too many waypoints.")
        return tuple(
            GeoPoint(lat=item.lat, lng=item.lng, label=item.label.strip()) for item in stops
        )

    def _ensure_departure_window(
        self, departure: datetime, arrival: datetime, moment: datetime, *, publishing: bool
    ) -> None:
        if arrival <= departure:
            raise InvalidTransitionError("estimatedArrivalAt must be after departureAt.")
        if publishing and departure <= moment:
            raise InvalidTransitionError("departureAt must be in the future at publish time.")

    def _restrict_after_acceptances(
        self,
        trip: Trip,
        *,
        departure_at: datetime | None,
        stops: tuple[StopInput, ...] | None,
        total_seats: int | None,
    ) -> None:
        if stops is not None:
            raise InvalidTransitionError(
                "Route changes after acceptances require cancelling and republishing."
            )
        if departure_at is not None:
            delta = abs((departure_at - trip.departure_at).total_seconds()) / 60
            if delta > self._settings.trips_edit_departure_tolerance_minutes:
                raise InvalidTransitionError(
                    "A departure shift of more than 15 minutes requires "
                    "cancelling and republishing."
                )
        if total_seats is not None and total_seats < trip.total_seats:
            raise InvalidTransitionError(
                "Seats can only be increased after a passenger is accepted."
            )

    def _assert_version(self, trip: Trip, expected: int | None) -> None:
        if expected is None:
            raise PreconditionRequiredError("If-Match must be the current trip version.")
        if expected != trip.version:
            raise VersionConflictError("Reload the trip and retry the edit.")


def _notes(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if len(trimmed) > MAX_NOTES:
        raise ConflictError("Notes must be 500 characters or fewer.")
    return trimmed or None
