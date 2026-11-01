"""Join-request rules and the seat transaction (BR-JOIN-01..11)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy.exc import IntegrityError

from app.core.authz.permissions import Role
from app.core.config import Settings
from app.core.errors import (
    DuplicateRequestError,
    EmailNotVerifiedError,
    ForbiddenError,
    IdempotencyConflictError,
    IdentityNotVerifiedError,
    InvalidTransitionError,
    NotFoundError,
    PhoneNotVerifiedError,
    RequestNotPendingError,
    RouteIncompatibleError,
    SeatUnavailableError,
    TripNotAcceptingError,
    ValidationAppError,
)
from app.core.events import (
    EventPublisher,
    JoinRequestAccepted,
    JoinRequestCancelled,
    JoinRequestCreated,
    JoinRequestRejected,
    NoopEventPublisher,
)
from app.core.ids import uuid7
from app.core.lifecycle import BlockChecker, NoopBlockChecker
from app.modules.bookings.models import (
    NOTE_MAX_LENGTH,
    JoinCancelledBy,
    JoinRequestStatus,
    TripJoinRequest,
)
from app.modules.bookings.repository import (
    BookingRepository,
    account_is_active,
    identity_is_approved,
)
from app.modules.trips.models import Trip, TripStatus

log = structlog.get_logger("app.bookings")

_ACCEPTING = frozenset({TripStatus.PUBLISHED, TripStatus.FULL})
_RELEASABLE = frozenset({TripStatus.PUBLISHED, TripStatus.FULL, TripStatus.IN_PROGRESS})
_KEY_MAX = 200
_FRACTION = Decimal("0.00001")


@dataclass(frozen=True, slots=True)
class JoinPoint:
    lat: float
    lng: float
    label: str


@dataclass(frozen=True, slots=True)
class CallContact:
    user_id: UUID
    display_name: str
    phone: str


@dataclass(frozen=True, slots=True)
class JoinView:
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


def _constraint_name(exc: IntegrityError) -> str:
    orig = exc.orig
    name = getattr(orig, "constraint_name", None)
    if isinstance(name, str):
        return name
    return str(orig)


def _fraction(value: float) -> Decimal:
    return Decimal(str(value)).quantize(_FRACTION)


def _minutes_before(departure_at: datetime, now: datetime) -> int:
    return int((departure_at - now).total_seconds() // 60)


class BookingService:
    """Implements :class:`app.core.lifecycle.BookingBridge` for the composition root."""

    def __init__(
        self,
        repository: BookingRepository,
        settings: Settings,
        *,
        events: EventPublisher | None = None,
        blocks: BlockChecker | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._events = events or NoopEventPublisher()
        self._blocks = blocks or NoopBlockChecker()

    async def create(
        self,
        *,
        passenger_id: UUID,
        roles: frozenset[Role],
        email_verified: bool,
        phone_verified: bool,
        trip_id: UUID,
        seats_requested: int,
        pickup: JoinPoint,
        dropoff: JoinPoint,
        note: str | None,
        idempotency_key: str | None,
        now: datetime | None = None,
    ) -> JoinView:
        del now
        key = _require_key(idempotency_key)
        cleaned = _note(note)
        if Role.PASSENGER not in roles:
            raise ForbiddenError("A passenger role is required to request a seat.")
        _require_verified_contact(email_verified, phone_verified)
        self._check_seat_count(seats_requested)

        existing = await self._repository.get_by_idempotency(passenger_id, key)
        if existing is not None:
            await self._assert_same_payload(
                existing,
                seats_requested=seats_requested,
                pickup=pickup,
                dropoff=dropoff,
                note=cleaned,
            )
            return await self._view(existing)

        flags = await self._repository.passenger_flags(passenger_id)
        if flags is None or not account_is_active(flags[0]):
            raise ForbiddenError("Account is not active.")
        if self._settings.verification_identity_required_before_join and not identity_is_approved(
            flags[1]
        ):
            raise IdentityNotVerifiedError("Verify your identity before requesting a seat.")

        trip = await self._repository.lock_trip(trip_id)
        if trip is None or trip.status is TripStatus.DRAFT:
            raise NotFoundError("Trip not found.")
        if trip.driver_id == passenger_id:
            raise ForbiddenError("You cannot request a seat on your own trip.")
        if trip.status is not TripStatus.PUBLISHED:
            raise TripNotAcceptingError("This trip is not open for new requests.")
        if seats_requested > trip.available_seats:
            raise SeatUnavailableError("Not enough free seats on this trip.")
        if await self._blocks.is_blocked_either_way(
            self._repository.session, passenger_id, trip.driver_id
        ):
            raise NotFoundError("Trip not found.")

        fit = await self._repository.route_fractions(
            trip_id,
            pickup_lat=pickup.lat,
            pickup_lng=pickup.lng,
            dropoff_lat=dropoff.lat,
            dropoff_lng=dropoff.lng,
        )
        if fit is None:
            raise RouteIncompatibleError("Pickup and drop-off must lie on the route, in order.")

        request = TripJoinRequest(
            id=uuid7(),
            trip_id=trip_id,
            passenger_id=passenger_id,
            status=JoinRequestStatus.PENDING,
            seats_requested=seats_requested,
            pickup_point=self._repository.point(pickup.lat, pickup.lng),
            dropoff_point=self._repository.point(dropoff.lat, dropoff.lng),
            pickup_label=pickup.label.strip(),
            dropoff_label=dropoff.label.strip(),
            pickup_fraction=_fraction(fit[0]),
            dropoff_fraction=_fraction(fit[1]),
            note=cleaned,
            idempotency_key=key,
        )
        try:
            await self._repository.insert(request)
        except IntegrityError as exc:
            return await self._recover_insert(
                exc,
                passenger_id=passenger_id,
                trip_id=trip_id,
                key=key,
                seats_requested=seats_requested,
                pickup=pickup,
                dropoff=dropoff,
                note=cleaned,
            )
        log.info("join_request_created", trip_id=str(trip_id), request_id=str(request.id))
        await self._events.publish(
            JoinRequestCreated(
                request_id=request.id,
                trip_id=trip_id,
                driver_id=trip.driver_id,
                passenger_id=passenger_id,
                seats=seats_requested,
            )
        )
        return await self._view(request)

    async def get(self, request_id: UUID, *, viewer_id: UUID, is_admin: bool) -> JoinView:
        request = await self._repository.get(request_id)
        if request is None:
            raise NotFoundError("Join request not found.")
        trip = await self._repository.get_trip(request.trip_id)
        if trip is None:
            raise NotFoundError("Join request not found.")
        if not _can_read(request, trip, viewer_id=viewer_id, is_admin=is_admin):
            raise NotFoundError("Join request not found.")
        return await self._view(request)

    async def list_for_trip(
        self,
        trip_id: UUID,
        *,
        viewer_id: UUID,
        is_admin: bool,
        statuses: frozenset[JoinRequestStatus] | None,
        before: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[JoinView]:
        trip = await self._repository.get_trip(trip_id)
        if trip is None or (not is_admin and trip.driver_id != viewer_id):
            raise NotFoundError("Trip not found.")
        rows = await self._repository.list_for_trip(
            trip_id, statuses=statuses, before=before, limit=limit
        )
        return await self._views(rows)

    async def list_mine(
        self,
        passenger_id: UUID,
        *,
        statuses: frozenset[JoinRequestStatus] | None,
        before: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[JoinView]:
        rows = await self._repository.list_for_passenger(
            passenger_id, statuses=statuses, before=before, limit=limit
        )
        return await self._views(rows)

    async def accept(
        self, request_id: UUID, *, driver_id: UUID, now: datetime | None = None
    ) -> JoinView:
        moment = now or datetime.now(UTC)
        request = await self._repository.get(request_id)
        if request is None:
            raise NotFoundError("Join request not found.")
        trip = await self._repository.lock_trip(request.trip_id)
        locked = await self._repository.lock_request(request_id)
        if trip is None or locked is None or trip.driver_id != driver_id:
            raise NotFoundError("Join request not found.")
        if locked.status is not JoinRequestStatus.PENDING:
            raise RequestNotPendingError("Only a pending request can be accepted.")
        if trip.status not in _ACCEPTING:
            raise TripNotAcceptingError("This trip is no longer accepting passengers.")
        if locked.seats_requested > trip.available_seats:
            raise SeatUnavailableError("Not enough free seats on this trip.")
        _reserve(trip, locked.seats_requested)
        changed = await self._repository.mark(locked, status=JoinRequestStatus.ACCEPTED, now=moment)
        if not changed:
            raise RequestNotPendingError("Only a pending request can be accepted.")
        log.info("join_request_accepted", trip_id=str(trip.id), request_id=str(locked.id))
        await self._events.publish(
            JoinRequestAccepted(
                request_id=locked.id,
                trip_id=trip.id,
                driver_id=trip.driver_id,
                passenger_id=locked.passenger_id,
            )
        )
        return await self._view(locked)

    async def reject(
        self, request_id: UUID, *, driver_id: UUID, now: datetime | None = None
    ) -> JoinView:
        moment = now or datetime.now(UTC)
        request = await self._repository.get(request_id)
        if request is None:
            raise NotFoundError("Join request not found.")
        trip = await self._repository.lock_trip(request.trip_id)
        locked = await self._repository.lock_request(request_id)
        if trip is None or locked is None or trip.driver_id != driver_id:
            raise NotFoundError("Join request not found.")
        if locked.status is not JoinRequestStatus.PENDING:
            raise RequestNotPendingError("Only a pending request can be rejected.")
        changed = await self._repository.mark(locked, status=JoinRequestStatus.REJECTED, now=moment)
        if not changed:
            raise RequestNotPendingError("Only a pending request can be rejected.")
        log.info("join_request_rejected", trip_id=str(trip.id), request_id=str(locked.id))
        await self._events.publish(
            JoinRequestRejected(
                request_id=locked.id,
                trip_id=trip.id,
                driver_id=trip.driver_id,
                passenger_id=locked.passenger_id,
            )
        )
        return await self._view(locked)

    async def cancel(
        self, request_id: UUID, *, passenger_id: UUID, now: datetime | None = None
    ) -> JoinView:
        moment = now or datetime.now(UTC)
        request = await self._repository.get(request_id)
        if request is None or request.passenger_id != passenger_id:
            raise NotFoundError("Join request not found.")
        trip = await self._repository.lock_trip(request.trip_id)
        locked = await self._repository.lock_request(request_id)
        if trip is None or locked is None:
            raise NotFoundError("Join request not found.")
        if locked.status not in {JoinRequestStatus.PENDING, JoinRequestStatus.ACCEPTED}:
            raise InvalidTransitionError("This request can no longer be cancelled.")
        was_accepted = locked.status is JoinRequestStatus.ACCEPTED
        if was_accepted and trip.status in _RELEASABLE:
            _release(trip, locked.seats_requested)
        minutes = _minutes_before(trip.departure_at, moment)
        changed = await self._repository.mark(
            locked,
            status=JoinRequestStatus.CANCELLED,
            now=moment,
            cancelled_by=JoinCancelledBy.PASSENGER,
            minutes_before=minutes,
        )
        if not changed:
            raise InvalidTransitionError("This request can no longer be cancelled.")
        log.info("join_request_cancelled", trip_id=str(trip.id), request_id=str(locked.id))
        await self._events.publish(
            JoinRequestCancelled(
                request_id=locked.id,
                trip_id=trip.id,
                driver_id=trip.driver_id,
                passenger_id=locked.passenger_id,
                was_accepted=was_accepted,
            )
        )
        return await self._view(locked)

    async def on_trip_cancelled(self, trip_id: UUID, *, cancelled_by: str, now: datetime) -> None:
        trip = await self._repository.lock_trip(trip_id)
        if trip is None:
            return
        actor = JoinCancelledBy(cancelled_by)
        await self._repository.cancel_open_for_trip(
            trip_id,
            cancelled_by=actor,
            now=now,
            minutes_before=_minutes_before(trip.departure_at, now),
        )

    async def on_trip_completed(self, trip_id: UUID, *, now: datetime) -> None:
        del now
        await self._repository.complete_accepted(trip_id)

    async def is_accepted_passenger(self, trip_id: UUID, user_id: UUID) -> bool:
        return await self._repository.is_accepted(trip_id, user_id)

    async def call_contacts(self, trip_id: UUID, viewer_id: UUID) -> list[CallContact]:
        rows = await self._repository.verified_peer_phones(trip_id, viewer_id)
        return [
            CallContact(user_id=user_id, display_name=name, phone=phone)
            for user_id, name, phone in rows
        ]

    async def passenger_ids(self, trip_id: UUID, *, include_pending: bool) -> tuple[UUID, ...]:
        return await self._repository.passenger_ids(trip_id, include_pending=include_pending)

    async def list_passenger_trip_ids(
        self,
        user_id: UUID,
        *,
        statuses: frozenset[str] | None,
        before: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[UUID]:
        return await self._repository.passenger_trip_ids(
            user_id, statuses=statuses, before=before, limit=limit
        )

    async def expire_pending(self, now: datetime | None = None) -> int:
        moment = now or datetime.now(UTC)
        count = await self._repository.expire_pending(moment)
        if count:
            log.info("join_requests_expired", count=count)
        return count

    async def count_recent_cancellations(self, user_id: UUID) -> int:
        return await self._repository.count_recent_cancellations(
            user_id, days=self._settings.bookings_cancellation_window_days
        )

    def _check_seat_count(self, seats_requested: int) -> None:
        cap = min(
            self._settings.bookings_max_seats_per_request,
            self._settings.trips_max_passenger_seats,
        )
        if seats_requested < 1 or seats_requested > cap:
            raise ValidationAppError(f"seatsRequested must be between 1 and {cap}.")

    async def _recover_insert(
        self,
        exc: IntegrityError,
        *,
        passenger_id: UUID,
        trip_id: UUID,
        key: str,
        seats_requested: int,
        pickup: JoinPoint,
        dropoff: JoinPoint,
        note: str | None,
    ) -> JoinView:
        del trip_id
        name = _constraint_name(exc)
        if "fractions" in name:
            raise RouteIncompatibleError(
                "Pickup and drop-off must lie on the route, in order."
            ) from exc
        existing = await self._repository.get_by_idempotency(passenger_id, key)
        if existing is not None:
            await self._assert_same_payload(
                existing,
                seats_requested=seats_requested,
                pickup=pickup,
                dropoff=dropoff,
                note=note,
            )
            return await self._view(existing)
        raise DuplicateRequestError("You already have an active request for this trip.") from exc

    async def _assert_same_payload(
        self,
        existing: TripJoinRequest,
        *,
        seats_requested: int,
        pickup: JoinPoint,
        dropoff: JoinPoint,
        note: str | None,
    ) -> None:
        pickup_lat, pickup_lng = await self._repository.point_lat_lng(existing.pickup_point)
        dropoff_lat, dropoff_lng = await self._repository.point_lat_lng(existing.dropoff_point)
        same = (
            existing.seats_requested == seats_requested
            and round(pickup_lat, 5) == round(pickup.lat, 5)
            and round(pickup_lng, 5) == round(pickup.lng, 5)
            and round(dropoff_lat, 5) == round(dropoff.lat, 5)
            and round(dropoff_lng, 5) == round(dropoff.lng, 5)
            and (existing.note or None) == note
        )
        if not same:
            raise IdempotencyConflictError(
                "This Idempotency-Key was already used for a different request."
            )

    async def _views(self, rows: list[TripJoinRequest]) -> list[JoinView]:
        return [await self._view(row) for row in rows]

    async def _view(self, request: TripJoinRequest) -> JoinView:
        pickup_lat, pickup_lng = await self._repository.point_lat_lng(request.pickup_point)
        dropoff_lat, dropoff_lng = await self._repository.point_lat_lng(request.dropoff_point)
        names = await self._repository.display_names((request.passenger_id,))
        verified = await self._repository.identity_verified((request.passenger_id,))
        cancellations = await self._repository.cancellation_counts(
            (request.passenger_id,), days=self._settings.bookings_cancellation_window_days
        )
        return JoinView(
            id=request.id,
            trip_id=request.trip_id,
            passenger_id=request.passenger_id,
            status=request.status,
            seats_requested=request.seats_requested,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            dropoff_lat=dropoff_lat,
            dropoff_lng=dropoff_lng,
            pickup_label=request.pickup_label,
            dropoff_label=request.dropoff_label,
            pickup_fraction=float(request.pickup_fraction),
            dropoff_fraction=float(request.dropoff_fraction),
            note=request.note,
            created_at=request.created_at,
            responded_at=request.responded_at,
            cancelled_at=request.cancelled_at,
            cancelled_by=request.cancelled_by,
            minutes_before_departure_at_cancel=request.minutes_before_departure_at_cancel,
            passenger_display_name=names.get(request.passenger_id, ""),
            passenger_identity_verified=verified.get(request.passenger_id, False),
            passenger_cancellations_last_90_days=cancellations.get(request.passenger_id, 0),
        )


def _require_verified_contact(email_verified: bool, phone_verified: bool) -> None:
    if not email_verified:
        raise EmailNotVerifiedError("Confirm your email before requesting a seat.")
    if not phone_verified:
        raise PhoneNotVerifiedError("Confirm your mobile number before requesting a seat.")


def _reserve(trip: Trip, seats: int) -> None:
    trip.available_seats -= seats
    if trip.available_seats == 0 and trip.status is TripStatus.PUBLISHED:
        trip.status = TripStatus.FULL
    trip.version += 1


def _release(trip: Trip, seats: int) -> None:
    trip.available_seats += seats
    if trip.status is TripStatus.FULL and trip.available_seats > 0:
        trip.status = TripStatus.PUBLISHED
    trip.version += 1


def _can_read(request: TripJoinRequest, trip: Trip, *, viewer_id: UUID, is_admin: bool) -> bool:
    return is_admin or viewer_id in {request.passenger_id, trip.driver_id}


def _require_key(value: str | None) -> str:
    if value is None or not value.strip():
        raise ValidationAppError("Idempotency-Key is required.")
    key = value.strip()
    if len(key) > _KEY_MAX:
        raise ValidationAppError("Idempotency-Key is too long.")
    return key


def _note(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if len(trimmed) > NOTE_MAX_LENGTH:
        raise ValidationAppError("Note must be 300 characters or fewer.")
    return trimmed
