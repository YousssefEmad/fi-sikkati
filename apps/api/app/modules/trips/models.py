"""``trips``, ``trip_routes`` and ``trip_stops`` (database.md §2.3)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Final
from uuid import UUID

from geoalchemy2 import Geography, Geometry
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, uuid_primary_key


class TripStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    FULL = "FULL"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class StopKind(StrEnum):
    ORIGIN = "ORIGIN"
    WAYPOINT = "WAYPOINT"
    DESTINATION = "DESTINATION"


class CancelledBy(StrEnum):
    DRIVER = "DRIVER"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


ACTIVE_TRIP_STATUSES: Final[frozenset[TripStatus]] = frozenset(
    {TripStatus.PUBLISHED, TripStatus.FULL, TripStatus.IN_PROGRESS}
)
TERMINAL_STATUSES: Final[frozenset[TripStatus]] = frozenset(
    {TripStatus.COMPLETED, TripStatus.CANCELLED, TripStatus.EXPIRED}
)
DELETION_BLOCKING_STATUSES: Final[frozenset[TripStatus]] = frozenset(
    {TripStatus.PUBLISHED, TripStatus.FULL, TripStatus.IN_PROGRESS}
)


def _pg_enum(enum: type[StrEnum], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda members: [m.value for m in members])


TRIP_STATUS_ENUM: Final = _pg_enum(TripStatus, "trips_status_enum")
STOP_KIND_ENUM: Final = _pg_enum(StopKind, "trip_stops_kind_enum")
CANCELLED_BY_ENUM: Final = _pg_enum(CancelledBy, "trips_cancelled_by_enum")

GEOG_POINT: Final = Geography(geometry_type="POINT", srid=4326)
GEOM_LINE: Final = Geometry(geometry_type="LINESTRING", srid=4326)
GEOG_POLY: Final = Geography(geometry_type="POLYGON", srid=4326)


class Trip(Base, TimestampMixin):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint("total_seats >= 1", name="total_seats_positive"),
        CheckConstraint(
            "available_seats >= 0 AND available_seats <= total_seats",
            name="available_seats_range",
        ),
        CheckConstraint("estimated_arrival_at > departure_at", name="arrival_after_departure"),
        CheckConstraint("char_length(notes) <= 500", name="notes_length"),
        CheckConstraint("char_length(currency) = 3", name="currency_iso"),
        CheckConstraint("version >= 1", name="version_positive"),
        Index("ix_trips_status_departure_at", "status", "departure_at"),
        Index("ix_trips_driver_id_departure_at", "driver_id", "departure_at"),
        Index("ix_trips_origin_point", "origin_point", postgresql_using="gist"),
        Index("ix_trips_destination_point", "destination_point", postgresql_using="gist"),
        Index(
            "ix_trips_published_departure",
            "departure_at",
            postgresql_where=text("status IN ('PUBLISHED', 'FULL')"),
        ),
        Index(
            "uq_trips_driver_idempotency_key",
            "driver_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = uuid_primary_key()
    driver_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    vehicle_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[TripStatus] = mapped_column(
        TRIP_STATUS_ENUM,
        nullable=False,
        default=TripStatus.DRAFT,
        server_default=TripStatus.DRAFT.value,
    )
    departure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estimated_arrival_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    available_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    origin_label: Mapped[str] = mapped_column(Text, nullable=False)
    destination_label: Mapped[str] = mapped_column(Text, nullable=False)
    origin_point: Mapped[Any] = mapped_column(GEOG_POINT, nullable=False)
    destination_point: Mapped[Any] = mapped_column(GEOG_POINT, nullable=False)
    origin_area_point: Mapped[Any] = mapped_column(GEOG_POINT, nullable=False)
    destination_area_point: Mapped[Any] = mapped_column(GEOG_POINT, nullable=False)
    pricing_rule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pricing_rules.id", ondelete="RESTRICT"), nullable=True
    )
    price_per_seat_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    platform_fee_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    driver_amount_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="EGP", server_default="EGP")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[CancelledBy | None] = mapped_column(CANCELLED_BY_ENUM, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    route: Mapped[TripRoute | None] = relationship(
        back_populates="trip", cascade="all, delete-orphan", uselist=False, lazy="selectin"
    )
    stops: Mapped[list[TripStop]] = relationship(
        back_populates="trip",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="TripStop.sequence",
    )


class TripRoute(Base, TimestampMixin):
    __tablename__ = "trip_routes"
    __table_args__ = (
        CheckConstraint("distance_m >= 0", name="distance_non_negative"),
        CheckConstraint("duration_s >= 0", name="duration_non_negative"),
        Index("ix_trip_routes_corridor", "corridor", postgresql_using="gist"),
        Index("ix_trip_routes_geometry", "geometry", postgresql_using="gist"),
    )

    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), primary_key=True
    )
    geometry: Mapped[Any] = mapped_column(GEOM_LINE, nullable=False)
    corridor: Mapped[Any] = mapped_column(GEOG_POLY, nullable=False)
    distance_m: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_s: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    provider_ref: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    trip: Mapped[Trip] = relationship(back_populates="route")


class TripStop(Base, TimestampMixin):
    __tablename__ = "trip_stops"
    __table_args__ = (
        UniqueConstraint("trip_id", "sequence", name="uq_trip_stops_trip_id_sequence"),
        CheckConstraint("route_fraction >= 0 AND route_fraction <= 1", name="route_fraction_range"),
    )

    id: Mapped[UUID] = uuid_primary_key()
    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[StopKind] = mapped_column(STOP_KIND_ENUM, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    point: Mapped[Any] = mapped_column(GEOG_POINT, nullable=False)
    route_fraction: Mapped[float] = mapped_column(Numeric(6, 5), nullable=False)

    trip: Mapped[Trip] = relationship(back_populates="stops")
