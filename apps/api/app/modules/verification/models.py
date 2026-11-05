"""``identity_documents`` and ``driver_verifications`` (database.md §2.2)."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, uuid_primary_key


class IdentityDocumentType(StrEnum):
    NATIONAL_ID_FRONT = "NATIONAL_ID_FRONT"
    NATIONAL_ID_BACK = "NATIONAL_ID_BACK"
    SELFIE = "SELFIE"


class ReviewStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DriverVerificationStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"


# Front of the national ID is enough to submit; back and selfie stay optional helpers.
REQUIRED_IDENTITY_DOCUMENT_TYPES: Final[frozenset[IdentityDocumentType]] = frozenset(
    {
        IdentityDocumentType.NATIONAL_ID_FRONT,
    }
)


def _pg_enum(enum: type[StrEnum], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda members: [m.value for m in members])


IDENTITY_DOCUMENT_TYPE_ENUM: Final = _pg_enum(
    IdentityDocumentType, "identity_documents_document_type_enum"
)
IDENTITY_DOCUMENT_STATUS_ENUM: Final = _pg_enum(ReviewStatus, "identity_documents_status_enum")
DRIVER_VERIFICATION_STATUS_ENUM: Final = _pg_enum(
    DriverVerificationStatus, "driver_verifications_status_enum"
)


class IdentityDocument(Base, TimestampMixin):
    __tablename__ = "identity_documents"
    __table_args__ = (
        CheckConstraint(
            "status <> 'REJECTED' OR ("
            "rejection_reason IS NOT NULL AND char_length(rejection_reason) >= 3)",
            name="rejection_reason_required",
        ),
        Index("ix_identity_documents_user_id", "user_id"),
        Index("ix_identity_documents_status_created_at", "status", "created_at"),
    )

    id: Mapped[UUID] = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[IdentityDocumentType] = mapped_column(
        IDENTITY_DOCUMENT_TYPE_ENUM, nullable=False
    )
    file_id: Mapped[UUID] = mapped_column(
        ForeignKey("stored_files.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[ReviewStatus] = mapped_column(
        IDENTITY_DOCUMENT_STATUS_ENUM,
        nullable=False,
        default=ReviewStatus.PENDING,
        server_default=ReviewStatus.PENDING.value,
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class DriverVerification(Base, TimestampMixin):
    __tablename__ = "driver_verifications"
    __table_args__ = (
        CheckConstraint(
            "status <> 'REJECTED' OR ("
            "rejection_reason IS NOT NULL AND char_length(rejection_reason) >= 3)",
            name="rejection_reason_required",
        ),
        Index("ix_driver_verifications_user_id", "user_id"),
        Index(
            "uq_driver_verifications_user_active",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'APPROVED')"),
        ),
    )

    id: Mapped[UUID] = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[DriverVerificationStatus] = mapped_column(
        DRIVER_VERIFICATION_STATUS_ENUM,
        nullable=False,
        default=DriverVerificationStatus.PENDING,
        server_default=DriverVerificationStatus.PENDING.value,
    )
    licence_file_id: Mapped[UUID] = mapped_column(
        ForeignKey("stored_files.id", ondelete="RESTRICT"), nullable=False
    )
    licence_expires_on: Mapped[date] = mapped_column(nullable=False)
    vehicle_id: Mapped[UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
