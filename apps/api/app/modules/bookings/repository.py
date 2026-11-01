"""SQL for join requests and the seat lock (BR-JOIN-03/05/06)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bookings.models import (
    ACTIVE_REQUEST_STATUSES,
    JoinCancelledBy,
    JoinRequestStatus,
    TripJoinRequest,
)
from app.modules.trips.geo import parse_point_wkt, point_wkt
from app.modules.trips.models import CancelledBy, Trip, TripStatus
from app.modules.users.models import AccountStatus, IdentityVerificationStatus, User, UserProfile

_ACTIVE = "status IN ('PENDING', 'ACCEPTED')"


class BookingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @property
    def session(self) -> AsyncSession:
        return self._db

    async def get(self, request_id: UUID) -> TripJoinRequest | None:
        return await self._db.get(TripJoinRequest, request_id)

    async def lock_request(self, request_id: UUID) -> TripJoinRequest | None:
        result = await self._db.execute(
            select(TripJoinRequest).where(TripJoinRequest.id == request_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_trip(self, trip_id: UUID) -> Trip | None:
        return await self._db.get(Trip, trip_id)

    async def lock_trip(self, trip_id: UUID) -> Trip | None:
        result = await self._db.execute(select(Trip).where(Trip.id == trip_id).with_for_update())
        return result.scalar_one_or_none()

    async def get_by_idempotency(
        self, passenger_id: UUID, idempotency_key: str
    ) -> TripJoinRequest | None:
        result = await self._db.execute(
            select(TripJoinRequest).where(
                TripJoinRequest.passenger_id == passenger_id,
                TripJoinRequest.idempotency_key == idempotency_key,
            )
        )
        return result.scalar_one_or_none()

    async def active_for_pair(self, trip_id: UUID, passenger_id: UUID) -> TripJoinRequest | None:
        result = await self._db.execute(
            select(TripJoinRequest).where(
                TripJoinRequest.trip_id == trip_id,
                TripJoinRequest.passenger_id == passenger_id,
                TripJoinRequest.status.in_(tuple(ACTIVE_REQUEST_STATUSES)),
            )
        )
        return result.scalar_one_or_none()

    async def insert(self, request: TripJoinRequest) -> None:
        """Insert inside a savepoint so a unique violation leaves the session usable."""
        async with self._db.begin_nested():
            self._db.add(request)
            await self._db.flush()
        await self._db.refresh(request)

    async def passenger_flags(self, user_id: UUID) -> tuple[str, str] | None:
        """Return ``(account_status, identity_status)`` or ``None`` when the user is missing."""
        row = await self._db.execute(
            select(User.status, User.identity_verification_status).where(User.id == user_id)
        )
        found = row.first()
        if found is None:
            return None
        return str(found[0]), str(found[1])

    async def route_fractions(
        self,
        trip_id: UUID,
        *,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
    ) -> tuple[float, float] | None:
        """BR-JOIN-04 / BR-MATCH-02: both points inside the corridor, pickup before drop-off."""
        row = await self._db.execute(
            text(
                """
                SELECT
                  ST_LineLocatePoint(
                    r.geometry, ST_SetSRID(ST_MakePoint(:plng, :plat), 4326)
                  ) AS pickup_fraction,
                  ST_LineLocatePoint(
                    r.geometry, ST_SetSRID(ST_MakePoint(:dlng, :dlat), 4326)
                  ) AS dropoff_fraction
                FROM trip_routes r
                WHERE r.trip_id = :trip_id
                  AND ST_Covers(
                    r.corridor,
                    ST_SetSRID(ST_MakePoint(:plng, :plat), 4326)::geography
                  )
                  AND ST_Covers(
                    r.corridor,
                    ST_SetSRID(ST_MakePoint(:dlng, :dlat), 4326)::geography
                  )
                  AND ST_LineLocatePoint(
                    r.geometry, ST_SetSRID(ST_MakePoint(:plng, :plat), 4326)
                  ) < ST_LineLocatePoint(
                    r.geometry, ST_SetSRID(ST_MakePoint(:dlng, :dlat), 4326)
                  )
                """
            ),
            {
                "trip_id": trip_id,
                "plat": pickup_lat,
                "plng": pickup_lng,
                "dlat": dropoff_lat,
                "dlng": dropoff_lng,
            },
        )
        found = row.first()
        if found is None:
            return None
        return float(found[0]), float(found[1])

    async def point_lat_lng(self, value: object) -> tuple[float, float]:
        wkt = await self._db.scalar(select(func.ST_AsText(value)))
        if not isinstance(wkt, str):
            return (0.0, 0.0)
        return parse_point_wkt(wkt)

    def point(self, lat: float, lng: float) -> object:
        return point_wkt(lat, lng)

    async def list_for_trip(
        self,
        trip_id: UUID,
        *,
        statuses: frozenset[JoinRequestStatus] | None,
        before: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[TripJoinRequest]:
        query = select(TripJoinRequest).where(TripJoinRequest.trip_id == trip_id)
        if statuses:
            query = query.where(TripJoinRequest.status.in_(tuple(statuses)))
        if before is not None:
            created_at, request_id = before
            query = query.where(
                (TripJoinRequest.created_at < created_at)
                | ((TripJoinRequest.created_at == created_at) & (TripJoinRequest.id < request_id))
            )
        query = query.order_by(TripJoinRequest.created_at.desc(), TripJoinRequest.id.desc())
        query = query.limit(limit)
        result = await self._db.execute(query)
        return list(result.scalars())

    async def list_for_passenger(
        self,
        passenger_id: UUID,
        *,
        statuses: frozenset[JoinRequestStatus] | None,
        before: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[TripJoinRequest]:
        query = select(TripJoinRequest).where(TripJoinRequest.passenger_id == passenger_id)
        if statuses:
            query = query.where(TripJoinRequest.status.in_(tuple(statuses)))
        if before is not None:
            created_at, request_id = before
            query = query.where(
                (TripJoinRequest.created_at < created_at)
                | ((TripJoinRequest.created_at == created_at) & (TripJoinRequest.id < request_id))
            )
        query = query.order_by(TripJoinRequest.created_at.desc(), TripJoinRequest.id.desc())
        query = query.limit(limit)
        result = await self._db.execute(query)
        return list(result.scalars())

    async def passenger_trip_ids(
        self,
        passenger_id: UUID,
        *,
        statuses: frozenset[str] | None,
        before: tuple[datetime, UUID] | None,
        limit: int,
    ) -> list[UUID]:
        """Trips where this passenger has an accepted or completed request."""
        query = (
            select(Trip.id)
            .join(TripJoinRequest, TripJoinRequest.trip_id == Trip.id)
            .where(
                TripJoinRequest.passenger_id == passenger_id,
                TripJoinRequest.status.in_(
                    (JoinRequestStatus.ACCEPTED, JoinRequestStatus.COMPLETED)
                ),
            )
        )
        if statuses:
            query = query.where(Trip.status.in_(tuple(TripStatus(item) for item in statuses)))
        if before is not None:
            departure_at, trip_id = before
            query = query.where(
                (Trip.departure_at < departure_at)
                | ((Trip.departure_at == departure_at) & (Trip.id < trip_id))
            )
        query = query.order_by(Trip.departure_at.desc(), Trip.id.desc()).limit(limit)
        result = await self._db.execute(query)
        return list(result.scalars())

    async def passenger_ids(self, trip_id: UUID, *, include_pending: bool) -> tuple[UUID, ...]:
        statuses = [JoinRequestStatus.ACCEPTED, JoinRequestStatus.COMPLETED]
        if include_pending:
            statuses.append(JoinRequestStatus.PENDING)
        result = await self._db.execute(
            select(TripJoinRequest.passenger_id).where(
                TripJoinRequest.trip_id == trip_id,
                TripJoinRequest.status.in_(tuple(statuses)),
            )
        )
        return tuple(result.scalars())

    async def is_accepted(self, trip_id: UUID, passenger_id: UUID) -> bool:
        found = await self._db.scalar(
            select(TripJoinRequest.id).where(
                TripJoinRequest.trip_id == trip_id,
                TripJoinRequest.passenger_id == passenger_id,
                TripJoinRequest.status == JoinRequestStatus.ACCEPTED,
            )
        )
        return found is not None

    async def display_names(self, user_ids: Sequence[UUID]) -> dict[UUID, str]:
        if not user_ids:
            return {}
        result = await self._db.execute(
            select(UserProfile.user_id, UserProfile.display_name).where(
                UserProfile.user_id.in_(tuple(user_ids))
            )
        )
        return {row[0]: str(row[1]) for row in result}

    async def identity_verified(self, user_ids: Sequence[UUID]) -> dict[UUID, bool]:
        if not user_ids:
            return {}
        result = await self._db.execute(
            select(User.id, User.identity_verification_status).where(User.id.in_(tuple(user_ids)))
        )
        approved = IdentityVerificationStatus.APPROVED
        return {row[0]: row[1] is approved for row in result}

    async def cancellation_counts(self, user_ids: Sequence[UUID], *, days: int) -> dict[UUID, int]:
        if not user_ids:
            return {}
        cutoff = datetime.now(UTC) - timedelta(days=days)
        join_rows = await self._db.execute(
            select(TripJoinRequest.passenger_id, func.count())
            .where(
                TripJoinRequest.passenger_id.in_(tuple(user_ids)),
                TripJoinRequest.status == JoinRequestStatus.CANCELLED,
                TripJoinRequest.cancelled_by == JoinCancelledBy.PASSENGER,
                TripJoinRequest.cancelled_at >= cutoff,
            )
            .group_by(TripJoinRequest.passenger_id)
        )
        counts = {row[0]: int(row[1]) for row in join_rows}
        trip_rows = await self._db.execute(
            select(Trip.driver_id, func.count())
            .where(
                Trip.driver_id.in_(tuple(user_ids)),
                Trip.status == TripStatus.CANCELLED,
                Trip.cancelled_by == CancelledBy.DRIVER,
                Trip.cancelled_at >= cutoff,
            )
            .group_by(Trip.driver_id)
        )
        for driver_id, count in trip_rows:
            counts[driver_id] = counts.get(driver_id, 0) + int(count)
        return counts

    async def count_recent_cancellations(self, user_id: UUID, *, days: int) -> int:
        counts = await self.cancellation_counts((user_id,), days=days)
        return counts.get(user_id, 0)

    async def count_accepted(self, user_id: UUID) -> int:
        value = await self._db.scalar(
            select(func.count())
            .select_from(TripJoinRequest)
            .where(
                TripJoinRequest.passenger_id == user_id,
                TripJoinRequest.status == JoinRequestStatus.ACCEPTED,
            )
        )
        return int(value or 0)

    async def cancel_open_for_trip(
        self,
        trip_id: UUID,
        *,
        cancelled_by: JoinCancelledBy,
        now: datetime,
        minutes_before: int,
    ) -> int:
        result = await self._db.execute(
            update(TripJoinRequest)
            .where(
                TripJoinRequest.trip_id == trip_id,
                TripJoinRequest.status.in_((JoinRequestStatus.PENDING, JoinRequestStatus.ACCEPTED)),
            )
            .values(
                status=JoinRequestStatus.CANCELLED,
                cancelled_at=now,
                cancelled_by=cancelled_by,
                responded_at=now,
                minutes_before_departure_at_cancel=minutes_before,
            )
        )
        return int(result.rowcount or 0) if isinstance(result, CursorResult) else 0

    async def complete_accepted(self, trip_id: UUID) -> int:
        result = await self._db.execute(
            update(TripJoinRequest)
            .where(
                TripJoinRequest.trip_id == trip_id,
                TripJoinRequest.status == JoinRequestStatus.ACCEPTED,
            )
            .values(status=JoinRequestStatus.COMPLETED)
        )
        return int(result.rowcount or 0) if isinstance(result, CursorResult) else 0

    async def expire_pending(self, now: datetime) -> int:
        """OD-014: a pending request ends when the trip's departure has passed. Idempotent."""
        result = await self._db.execute(
            text(
                """
                UPDATE trip_join_requests AS j
                SET status = 'EXPIRED',
                    responded_at = :now
                FROM trips AS t
                WHERE j.trip_id = t.id
                  AND j.status = 'PENDING'
                  AND t.departure_at <= :now
                """
            ),
            {"now": now},
        )
        return int(result.rowcount or 0) if isinstance(result, CursorResult) else 0

    async def mark(
        self,
        request: TripJoinRequest,
        *,
        status: JoinRequestStatus,
        now: datetime,
        cancelled_by: JoinCancelledBy | None = None,
        minutes_before: int | None = None,
    ) -> bool:
        """Transition only from the caller's expected current status. False means lost the race."""
        expected = request.status
        result = await self._db.execute(
            update(TripJoinRequest)
            .where(TripJoinRequest.id == request.id, TripJoinRequest.status == expected)
            .values(
                status=status,
                responded_at=now,
                cancelled_at=now if cancelled_by is not None else request.cancelled_at,
                cancelled_by=cancelled_by if cancelled_by is not None else request.cancelled_by,
                minutes_before_departure_at_cancel=(
                    minutes_before
                    if minutes_before is not None
                    else request.minutes_before_departure_at_cancel
                ),
            )
        )
        changed = isinstance(result, CursorResult) and bool(result.rowcount)
        if changed:
            await self._db.refresh(request)
        return changed

    async def verified_peer_phones(
        self, trip_id: UUID, viewer_id: UUID
    ) -> list[tuple[UUID, str, str]]:
        """Confirmed numbers of the other accepted people. Empty if the viewer is not one."""
        found = await self._db.execute(
            text(
                """
                WITH party AS (
                  SELECT driver_id AS user_id FROM trips WHERE id = :trip_id
                  UNION
                  SELECT passenger_id FROM trip_join_requests
                  WHERE trip_id = :trip_id AND status IN ('ACCEPTED', 'COMPLETED')
                )
                SELECT u.id, p.display_name, u.phone_e164
                FROM party
                JOIN users u ON u.id = party.user_id
                JOIN user_profiles p ON p.user_id = u.id
                WHERE EXISTS (SELECT 1 FROM party WHERE user_id = :viewer_id)
                  AND u.id <> :viewer_id
                  AND u.phone_verified_at IS NOT NULL
                  AND u.phone_e164 IS NOT NULL
                """
            ),
            {"trip_id": trip_id, "viewer_id": viewer_id},
        )
        return [(row[0], str(row[1]), str(row[2])) for row in found]


def account_is_active(status: str) -> bool:
    return status == AccountStatus.ACTIVE.value


def identity_is_approved(status: str) -> bool:
    return status == IdentityVerificationStatus.APPROVED.value
