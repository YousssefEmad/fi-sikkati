"""``vehicles`` and ``vehicle_documents`` (database.md §2.2)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, uuid_primary_key


class VehicleType(StrEnum):
    SEDAN = "SEDAN"
    HATCHBACK = "HATCHBACK"
    SUV = "SUV"
    VAN = "VAN"
    MINIBUS = "MINIBUS"
    OTHER = "OTHER"


class VehicleStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ReviewStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class VehicleDocumentType(StrEnum):
    REGISTRATION_FRONT = "REGISTRATION_FRONT"
    REGISTRATION_BACK = "REGISTRATION_BACK"
    VEHICLE_PHOTO = "VEHICLE_PHOTO"


REQUIRED_VEHICLE_DOCUMENT_TYPES: Final[frozenset[VehicleDocumentType]] = frozenset(
    {VehicleDocumentType.REGISTRATION_FRONT, VehicleDocumentType.REGISTRATION_BACK}
)


def _pg_enum(enum: type[StrEnum], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda members: [m.value for m in members])


VEHICLE_TYPE_ENUM: Final = _pg_enum(VehicleType, "vehicles_vehicle_type_enum")
VEHICLE_STATUS_ENUM: Final = _pg_enum(VehicleStatus, "vehicles_status_enum")
VEHICLE_VERIFICATION_ENUM: Final = _pg_enum(ReviewStatus, "vehicles_verification_status_enum")
VEHICLE_DOCUMENT_TYPE_ENUM: Final = _pg_enum(
    VehicleDocumentType, "vehicle_documents_document_type_enum"
)
VEHICLE_DOCUMENT_STATUS_ENUM: Final = _pg_enum(ReviewStatus, "vehicle_documents_status_enum")


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("year >= 1980 AND year <= 2100", name="year_range"),
        CheckConstraint("seat_capacity >= 2 AND seat_capacity <= 20", name="seat_capacity_range"),
        Index("ix_vehicles_owner_user_id", "owner_user_id"),
        Index(
            "ix_vehicles_verification_pending",
            "verification_status",
            postgresql_where=text("verification_status = 'PENDING'"),
        ),
    )

    id: Mapped[UUID] = uuid_primary_key()
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    make: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    color: Mapped[str] = mapped_column(Text, nullable=False)
    vehicle_type: Mapped[VehicleType] = mapped_column(VEHICLE_TYPE_ENUM, nullable=False)
    seat_capacity: Mapped[int] = mapped_column(nullable=False)
    plate_number: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[VehicleStatus] = mapped_column(
        VEHICLE_STATUS_ENUM,
        nullable=False,
        default=VehicleStatus.ACTIVE,
        server_default=VehicleStatus.ACTIVE.value,
    )
    verification_status: Mapped[ReviewStatus] = mapped_column(
        VEHICLE_VERIFICATION_ENUM,
        nullable=False,
        default=ReviewStatus.PENDING,
        server_default=ReviewStatus.PENDING.value,
    )

    documents: Mapped[list[VehicleDocument]] = relationship(
        back_populates="vehicle", cascade="all, delete-orphan", lazy="selectin"
    )


class VehicleDocument(Base, TimestampMixin):
    __tablename__ = "vehicle_documents"
    __table_args__ = (
        CheckConstraint(
            "status <> 'REJECTED' OR ("
            "rejection_reason IS NOT NULL AND char_length(rejection_reason) >= 3)",
            name="rejection_reason_required",
        ),
        Index("ix_vehicle_documents_vehicle_id", "vehicle_id"),
    )

    id: Mapped[UUID] = uuid_primary_key()
    vehicle_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[VehicleDocumentType] = mapped_column(
        VEHICLE_DOCUMENT_TYPE_ENUM, nullable=False
    )
    file_id: Mapped[UUID] = mapped_column(
        ForeignKey("stored_files.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[ReviewStatus] = mapped_column(
        VEHICLE_DOCUMENT_STATUS_ENUM,
        nullable=False,
        default=ReviewStatus.PENDING,
        server_default=ReviewStatus.PENDING.value,
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    vehicle: Mapped[Vehicle] = relationship(back_populates="documents")
