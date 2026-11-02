"""SQL for trips, routes and stops."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import bindparam, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.ids import uuid7
from app.modules.maps.geo import deterministic_jitter
from app.modules.maps.ports import GeoPoint, RouteResult
from app.modules.trips.geo import parse_linestring_wkt, parse_point_wkt, point_wkt
from app.modules.trips.models import (
    ACTIVE_TRIP_STATUSES,
    DELETION_BLOCKING_STATUSES,
    StopKind,
    Trip,
    TripRoute,
    TripStatus,
    TripStop,
)
from app.modules.vehicles.models import ReviewStatus, Vehicle, VehicleStatus

_PUBLISHED_MATCH_SQL = """
            WITH ranked AS (
              SELECT
                t.id AS trip_id,
                t.driver_id,
                t.vehicle_id,
                t.departure_at,
                t.estimated_arrival_at,
                t.total_seats,
                t.available_seats,
                t.origin_label,
                t.destination_label,
                ST_Y(t.origin_area_point::geometry) AS origin_lat,
                ST_X(t.origin_area_point::geometry) AS origin_lng,
                ST_Y(t.destination_area_point::geometry) AS destination_lat,
                ST_X(t.destination_area_point::geometry) AS destination_lng,
                t.price_per_seat_minor,
                t.currency,
                v.vehicle_type::text AS vehicle_type,
                p.display_name AS driver_display_name,
                (u.identity_verification_status = 'APPROVED') AS identity_verified,
                ROUND(ST_Distance(
                  r.geometry::geography,
                  ST_SetSRID(ST_MakePoint(:plng, :plat), 4326)::geography
                ))::int AS pickup_distance_m,
                ROUND(ST_Distance(
                  r.geometry::geography,
                  ST_SetSRID(ST_MakePoint(:dlng, :dlat), 4326)::geography
                ))::int AS dropoff_distance_m,
                ABS(EXTRACT(EPOCH FROM (t.departure_at - :requested_at)))::int
                  AS time_diff_s,
                CASE WHEN EXISTS (
                  SELECT 1 FROM trip_stops pu
                  JOIN trip_stops dr
                    ON dr.trip_id = pu.trip_id AND pu.sequence < dr.sequence
                  WHERE pu.trip_id = t.id
                    AND ST_DWithin(
                      pu.point,
                      ST_SetSRID(ST_MakePoint(:plng, :plat), 4326)::geography,
                      :stop_m
                    )
                    AND ST_DWithin(
                      dr.point,
                      ST_SetSRID(ST_MakePoint(:dlng, :dlat), 4326)::geography,
                      :stop_m
                    )
                ) THEN 1 ELSE 0 END AS exact_match
              FROM trips t
              JOIN trip_routes r ON r.trip_id = t.id
              JOIN vehicles v ON v.id = t.vehicle_id
              JOIN users u ON u.id = t.driver_id
              JOIN user_profiles p ON p.user_id = t.driver_id
              WHERE t.status = 'PUBLISHED'
                AND t.available_seats >= :seats
                AND t.departure_at >= :window_from
                AND t.departure_at <= :window_to
                AND ST_Covers(
                  r.corridor,
                  ST_SetSRID(ST_MakePoint(:plng, :plat), 4326)::geography
                )
                AND ST_Covers(
                  r.corridor,
                  ST_SetSRID(ST_MakePoint(:dlng, :dlat), 4326)::geography
                )
                AND ST_LineLocatePoint(
                  r.geometry,
                  ST_SetSRID(ST_MakePoint(:plng, :plat), 4326)
                ) < ST_LineLocatePoint(
                  r.geometry,
                  ST_SetSRID(ST_MakePoint(:dlng, :dlat), 4326)
                )
                __FILTERS__
            )
            SELECT
              ranked.*,
              (ranked.pickup_distance_m + ranked.dropoff_distance_m) AS distance_sum_m
            FROM ranked
            WHERE 1=1
            __CURSOR__
            ORDER BY
              ranked.exact_match DESC,
              (ranked.pickup_distance_m + ranked.dropoff_distance_m) ASC,
              ranked.time_diff_s ASC,
              ranked.available_seats DESC,
              ranked.departure_at ASC,
              ranked.trip_id ASC
            LIMIT :limit
        """


@dataclass(frozen=True, slots=True)
class MatchCursor:
    exact: int
    distance_sum_m: int
    time_diff_s: int
    available_seats: int
    departure_at: datetime
    trip_id: UUID


@dataclass(frozen=True, slots=True)
class PublishedMatch:
    trip_id: UUID
    driver_id: UUID
    vehicle_id: UUID
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
    price_per_seat_minor: int | None
    currency: str
    vehicle_type: str
    driver_display_name: str
    identity_verified: bool
    exact_match: bool
    pickup_distance_m: int
    dropoff_distance_m: int
    time_diff_s: int


class TripRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get(self, trip_id: UUID) -> Trip | None:
        result = await self._db.execute(
            select(Trip)
            .options(selectinload(Trip.route), selectinload(Trip.stops))
            .where(Trip.id == trip_id)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency(self, driver_id: UUID, key: str) -> Trip | None:
        result = await self._db.execute(
            select(Trip)
            .options(selectinload(Trip.route), selectinload(Trip.stops))
            .where(Trip.driver_id == driver_id, Trip.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def list_for_driver(
        self,
        driver_id: UUID,
        *,
        statuses: frozenset[TripStatus] | None,
        before_departure: datetime | None,
        before_id: UUID | None,
        limit: int,
    ) -> list[Trip]:
        stmt = (
            select(Trip)
            .options(selectinload(Trip.route), selectinload(Trip.stops))
            .where(Trip.driver_id == driver_id)
            .order_by(Trip.departure_at.desc(), Trip.id.desc())
            .limit(limit)
        )
        if statuses:
            stmt = stmt.where(Trip.status.in_(statuses))
        if before_departure is not None and before_id is not None:
            stmt = stmt.where(
                or_(
                    Trip.departure_at < before_departure,
                    (Trip.departure_at == before_departure) & (Trip.id < before_id),
                )
            )
        result = await self._db.execute(stmt)
        return list(result.scalars())

    async def overlapping(
        self,
        driver_id: UUID,
        *,
        departure_at: datetime,
        estimated_arrival_at: datetime,
        exclude_id: UUID | None = None,
    ) -> Trip | None:
        stmt = select(Trip).where(
            Trip.driver_id == driver_id,
            Trip.status.in_(ACTIVE_TRIP_STATUSES),
            Trip.departure_at < estimated_arrival_at,
            Trip.estimated_arrival_at > departure_at,
        )
        if exclude_id is not None:
            stmt = stmt.where(Trip.id != exclude_id)
        result = await self._db.execute(stmt.limit(1))
        return result.scalar_one_or_none()

    async def count_blocking_deletion(self, user_id: UUID) -> int:
        result = await self._db.execute(
            select(func.count())
            .select_from(Trip)
            .where(Trip.driver_id == user_id, Trip.status.in_(DELETION_BLOCKING_STATUSES))
        )
        return int(result.scalar_one())

    async def get_eligible_vehicle(self, vehicle_id: UUID, owner_id: UUID) -> Vehicle | None:
        result = await self._db.execute(
            select(Vehicle).where(
                Vehicle.id == vehicle_id,
                Vehicle.owner_user_id == owner_id,
                Vehicle.status == VehicleStatus.ACTIVE,
                Vehicle.verification_status == ReviewStatus.APPROVED,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        driver_id: UUID,
        vehicle_id: UUID,
        departure_at: datetime,
        estimated_arrival_at: datetime,
        total_seats: int,
        origin: GeoPoint,
        destination: GeoPoint,
        blur_meters: int,
        trip_id: UUID,
        notes: str | None,
        idempotency_key: str | None,
        currency: str,
    ) -> Trip:
        origin_area = deterministic_jitter(
            origin.lat, origin.lng, trip_id=trip_id, radius_m=blur_meters
        )
        dest_area = deterministic_jitter(
            destination.lat, destination.lng, trip_id=trip_id, radius_m=blur_meters
        )
        trip = Trip(
            id=trip_id,
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            departure_at=departure_at,
            estimated_arrival_at=estimated_arrival_at,
            total_seats=total_seats,
            available_seats=total_seats,
            origin_label=origin.label,
            destination_label=destination.label,
            origin_point=point_wkt(origin.lat, origin.lng),
            destination_point=point_wkt(destination.lat, destination.lng),
            origin_area_point=point_wkt(origin_area[0], origin_area[1]),
            destination_area_point=point_wkt(dest_area[0], dest_area[1]),
            notes=notes,
            idempotency_key=idempotency_key,
            currency=currency,
        )
        trip.stops = []
        self._db.add(trip)
        await self._db.flush()
        return trip

    async def replace_stops(
        self,
        trip: Trip,
        stops: tuple[tuple[int, StopKind, GeoPoint, float], ...],
    ) -> None:
        await self._db.execute(text("DELETE FROM trip_stops WHERE trip_id = :id"), {"id": trip.id})
        for sequence, kind, point, fraction in stops:
            self._db.add(
                TripStop(
                    id=uuid7(),
                    trip_id=trip.id,
                    sequence=sequence,
                    kind=kind,
                    label=point.label,
                    point=point_wkt(point.lat, point.lng),
                    route_fraction=fraction,
                )
            )
        await self._db.flush()

    async def upsert_route(
        self,
        trip: Trip,
        result: RouteResult,
        *,
        corridor_meters: int,
        computed_at: datetime,
    ) -> None:
        await self._db.execute(text("DELETE FROM trip_routes WHERE trip_id = :id"), {"id": trip.id})
        await self._db.execute(
            text(
                """
                INSERT INTO trip_routes (
                    trip_id, geometry, corridor, distance_m, duration_s,
                    provider, provider_ref, computed_at, created_at, updated_at
                ) VALUES (
                    :id,
                    ST_GeomFromText(:line, 4326),
                    ST_Buffer(ST_GeomFromText(:line, 4326)::geography, :meters),
                    :distance, :duration, :provider, :ref, :computed, now(), now()
                )
                """
            ),
            {
                "id": trip.id,
                "line": (
                    f"LINESTRING({', '.join(f'{lng} {lat}' for lng, lat in result.coordinates)})"
                ),
                "meters": corridor_meters,
                "distance": result.distance_m,
                "duration": result.duration_s,
                "provider": result.provider,
                "ref": result.provider_ref,
                "computed": computed_at,
            },
        )
        await self._db.flush()
        loaded = await self.get(trip.id)
        if loaded is not None:
            trip.route = loaded.route
            trip.stops = loaded.stops

    async def list_due_to_expire(self, cutoff: datetime) -> list[Trip]:
        result = await self._db.execute(
            select(Trip).where(
                Trip.status.in_((TripStatus.PUBLISHED, TripStatus.FULL)),
                Trip.departure_at <= cutoff,
            )
        )
        return list(result.scalars())

    async def list_due_to_complete(self, cutoff: datetime) -> list[Trip]:
        result = await self._db.execute(
            select(Trip).where(
                Trip.status == TripStatus.IN_PROGRESS,
                Trip.estimated_arrival_at <= cutoff,
            )
        )
        return list(result.scalars())

    async def purge_finished_before(self, cutoff: datetime) -> int:
        """Hard-delete finished/draft trips before ``cutoff`` and their trip chats.

        Join requests and ratings must go first (RESTRICT). Conversation rows cascade
        from ``trips``. Community chat is never touched. Raw SQL keeps this repository
        below the bookings/safety layers.
        """
        trip_ids = list(
            (
                await self._db.execute(
                    select(Trip.id).where(
                        Trip.status.in_(
                            (
                                TripStatus.COMPLETED,
                                TripStatus.CANCELLED,
                                TripStatus.EXPIRED,
                                TripStatus.DRAFT,
                            )
                        ),
                        Trip.departure_at < cutoff,
                    )
                )
            )
            .scalars()
            .all()
        )
        if not trip_ids:
            return 0
        ids_param = bindparam("ids", expanding=True)
        await self._db.execute(
            text("DELETE FROM ratings WHERE trip_id IN :ids").bindparams(ids_param),
            {"ids": trip_ids},
        )
        await self._db.execute(
            text("DELETE FROM trip_join_requests WHERE trip_id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"ids": trip_ids},
        )
        result = await self._db.execute(
            text("DELETE FROM trips WHERE id IN :ids").bindparams(
                bindparam("ids", expanding=True)
            ),
            {"ids": trip_ids},
        )
        return int(result.rowcount or 0)

    async def lock(self, trip_id: UUID) -> Trip | None:
        """Serialise seat changes and trip cancellation on one row (BR-JOIN-06)."""
        result = await self._db.execute(select(Trip).where(Trip.id == trip_id).with_for_update())
        return result.scalar_one_or_none()

    async def get_many(self, trip_ids: list[UUID]) -> list[Trip]:
        if not trip_ids:
            return []
        result = await self._db.execute(
            select(Trip)
            .where(Trip.id.in_(tuple(trip_ids)))
            .options(selectinload(Trip.route), selectinload(Trip.stops))
        )
        by_id = {row.id: row for row in result.scalars()}
        return [by_id[trip_id] for trip_id in trip_ids if trip_id in by_id]

    async def point_lat_lng(self, wkt_source: object) -> tuple[float, float]:
        value = await self._db.scalar(select(func.ST_AsText(wkt_source)))
        if not isinstance(value, str):
            return (0.0, 0.0)
        return parse_point_wkt(value)

    async def route_coordinates(self, route: TripRoute) -> tuple[tuple[float, float], ...]:
        value = await self._db.scalar(select(func.ST_AsText(route.geometry)))
        if not isinstance(value, str):
            return ()
        return parse_linestring_wkt(value)

    async def search_published(  # noqa: PLR0912
        self,
        *,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        window_from: datetime,
        window_to: datetime,
        requested_at: datetime,
        seats: int,
        stop_proximity_m: int,
        verified_only: bool,
        vehicle_type: str | None,
        price_max_minor: int | None,
        cursor: MatchCursor | None,
        limit: int,
        hidden_driver_ids: frozenset[UUID] | None = None,
        min_rating: float | None = None,
        rating_min_count: int = 3,
    ) -> list[PublishedMatch]:
        """BR-MATCH-01..07: corridor + direction + ranking, plus blocks and ratings."""
        filters = ""
        if verified_only:
            filters += " AND u.identity_verification_status = 'APPROVED'"
        if vehicle_type is not None:
            filters += " AND v.vehicle_type = :vehicle_type"
        if price_max_minor is not None:
            filters += " AND t.price_per_seat_minor <= :price_max"
        if hidden_driver_ids:
            placeholders = ", ".join(f":hid_{index}" for index in range(len(hidden_driver_ids)))
            filters += f" AND t.driver_id NOT IN ({placeholders})"
        if min_rating is not None:
            filters += """
                AND EXISTS (
                  SELECT 1 FROM ratings rt
                  WHERE rt.ratee_id = t.driver_id
                  GROUP BY rt.ratee_id
                  HAVING COUNT(*) >= :rating_min_count
                     AND AVG(rt.overall) >= :min_rating
                )
            """
        cursor_sql = ""
        if cursor is not None:
            cursor_sql = """
              AND (
                ranked.exact_match < :c_exact
                OR (ranked.exact_match = :c_exact AND ranked.distance_sum_m > :c_dist)
                OR (
                  ranked.exact_match = :c_exact AND ranked.distance_sum_m = :c_dist
                  AND ranked.time_diff_s > :c_tdiff
                )
                OR (
                  ranked.exact_match = :c_exact AND ranked.distance_sum_m = :c_dist
                  AND ranked.time_diff_s = :c_tdiff AND ranked.available_seats < :c_seats
                )
                OR (
                  ranked.exact_match = :c_exact AND ranked.distance_sum_m = :c_dist
                  AND ranked.time_diff_s = :c_tdiff AND ranked.available_seats = :c_seats
                  AND ranked.departure_at > :c_dep
                )
                OR (
                  ranked.exact_match = :c_exact AND ranked.distance_sum_m = :c_dist
                  AND ranked.time_diff_s = :c_tdiff AND ranked.available_seats = :c_seats
                  AND ranked.departure_at = :c_dep AND ranked.trip_id > :c_id
                )
              )
            """
        sql = _PUBLISHED_MATCH_SQL.replace("__FILTERS__", filters).replace("__CURSOR__", cursor_sql)
        params: dict[str, object] = {
            "plat": pickup_lat,
            "plng": pickup_lng,
            "dlat": dropoff_lat,
            "dlng": dropoff_lng,
            "window_from": window_from,
            "window_to": window_to,
            "requested_at": requested_at,
            "seats": seats,
            "stop_m": stop_proximity_m,
            "limit": limit,
        }
        if vehicle_type is not None:
            params["vehicle_type"] = vehicle_type
        if price_max_minor is not None:
            params["price_max"] = price_max_minor
        if hidden_driver_ids:
            for index, driver_id in enumerate(hidden_driver_ids):
                params[f"hid_{index}"] = driver_id
        if min_rating is not None:
            params["min_rating"] = min_rating
            params["rating_min_count"] = rating_min_count
        if cursor is not None:
            params["c_exact"] = cursor.exact
            params["c_dist"] = cursor.distance_sum_m
            params["c_tdiff"] = cursor.time_diff_s
            params["c_seats"] = cursor.available_seats
            params["c_dep"] = cursor.departure_at
            params["c_id"] = cursor.trip_id
        result = await self._db.execute(text(sql), params)
        rows: list[PublishedMatch] = []
        for row in result.mappings():
            rows.append(
                PublishedMatch(
                    trip_id=row["trip_id"],
                    driver_id=row["driver_id"],
                    vehicle_id=row["vehicle_id"],
                    departure_at=row["departure_at"],
                    estimated_arrival_at=row["estimated_arrival_at"],
                    total_seats=row["total_seats"],
                    available_seats=row["available_seats"],
                    origin_label=row["origin_label"],
                    destination_label=row["destination_label"],
                    origin_lat=float(row["origin_lat"]),
                    origin_lng=float(row["origin_lng"]),
                    destination_lat=float(row["destination_lat"]),
                    destination_lng=float(row["destination_lng"]),
                    price_per_seat_minor=row["price_per_seat_minor"],
                    currency=row["currency"],
                    vehicle_type=row["vehicle_type"],
                    driver_display_name=row["driver_display_name"],
                    identity_verified=bool(row["identity_verified"]),
                    exact_match=bool(row["exact_match"]),
                    pickup_distance_m=int(row["pickup_distance_m"]),
                    dropoff_distance_m=int(row["dropoff_distance_m"]),
                    time_diff_s=int(row["time_diff_s"]),
                )
            )
        return rows
