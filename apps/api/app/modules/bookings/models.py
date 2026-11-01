"""``trip_join_requests`` (database.md §2.4)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Final
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, uuid_primary_key
from app.modules.trips.models import GEOG_POINT


class JoinRequestStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    COMPLETED = "COMPLETED"


class JoinCancelledBy(StrEnum):
    PASSENGER = "PASSENGER"
    DRIVER = "DRIVER"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


ACTIVE_REQUEST_STATUSES: Final[frozenset[JoinRequestStatus]] = frozenset(
    {JoinRequestStatus.PENDING, JoinRequestStatus.ACCEPTED}
)


def _pg_enum(enum: type[StrEnum], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda members: [m.value for m in members])


JOIN_STATUS_ENUM: Final = _pg_enum(JoinRequestStatus, "trip_join_requests_status_enum")
JOIN_CANCELLED_BY_ENUM: Final = _pg_enum(JoinCancelledBy, "trip_join_requests_cancelled_by_enum")

NOTE_MAX_LENGTH = 300


class TripJoinRequest(Base, TimestampMixin):
    __tablename__ = "trip_join_requests"
    __table_args__ = (
        CheckConstraint("seats_requested >= 1", name="seats_positive"),
        CheckConstraint(
            "note IS NULL OR char_length(note) <= 300",
            name="note_length",
        ),
        CheckConstraint(
            "pickup_fraction >= 0 AND pickup_fraction <= 1 "
            "AND dropoff_fraction >= 0 AND dropoff_fraction <= 1 "
            "AND pickup_fraction < dropoff_fraction",
            name="fractions_ordered",
        ),
        Index(
            "uq_trip_join_requests_active_pair",
            "trip_id",
            "passenger_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'ACCEPTED')"),
        ),
        Index(
            "uq_trip_join_requests_passenger_idempotency",
            "passenger_id",
            "idempotency_key",
            unique=True,
        ),
        Index("ix_trip_join_requests_trip_id_status", "trip_id", "status"),
        Index("ix_trip_join_requests_passenger_created", "passenger_id", "created_at"),
        Index(
            "ix_trip_join_requests_pending",
            "status",
            "created_at",
            postgresql_where=text("status = 'PENDING'"),
        ),
    )

    id: Mapped[UUID] = uuid_primary_key()
    trip_id: Mapped[UUID] = mapped_column(
        ForeignKey("trips.id", ondelete="RESTRICT"), nullable=False
    )
    passenger_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[JoinRequestStatus] = mapped_column(
        JOIN_STATUS_ENUM,
        nullable=False,
        default=JoinRequestStatus.PENDING,
        server_default=JoinRequestStatus.PENDING.value,
    )
    seats_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    pickup_point: Mapped[Any] = mapped_column(GEOG_POINT, nullable=False)
    dropoff_point: Mapped[Any] = mapped_column(GEOG_POINT, nullable=False)
    pickup_label: Mapped[str] = mapped_column(Text, nullable=False)
    dropoff_label: Mapped[str] = mapped_column(Text, nullable=False)
    pickup_fraction: Mapped[float] = mapped_column(Numeric(6, 5), nullable=False)
    dropoff_fraction: Mapped[float] = mapped_column(Numeric(6, 5), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[JoinCancelledBy | None] = mapped_column(
        JOIN_CANCELLED_BY_ENUM, nullable=True
    )
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    minutes_before_departure_at_cancel: Mapped[int | None] = mapped_column(Integer, nullable=True)
