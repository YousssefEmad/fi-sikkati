"""``stored_files`` (database.md §2.2)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, uuid_primary_key


class StorageBucket(StrEnum):
    PUBLIC_MEDIA = "PUBLIC_MEDIA"
    PRIVATE_DOCUMENTS = "PRIVATE_DOCUMENTS"


class ScanStatus(StrEnum):
    NOT_SCANNED = "NOT_SCANNED"
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    SCAN_UNAVAILABLE = "SCAN_UNAVAILABLE"


def _pg_enum(enum: type[StrEnum], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda members: [m.value for m in members])


BUCKET_ENUM: Final = _pg_enum(StorageBucket, "stored_files_bucket_enum")
SCAN_STATUS_ENUM: Final = _pg_enum(ScanStatus, "stored_files_scan_status_enum")


class StoredFile(Base, TimestampMixin):
    """One object in S3/MinIO. Bytes never live in PostgreSQL."""

    __tablename__ = "stored_files"

    id: Mapped[UUID] = uuid_primary_key()
    bucket: Mapped[StorageBucket] = mapped_column(BUCKET_ENUM, nullable=False)
    object_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    owner_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    mime_type: Mapped[str] = mapped_column(Text, nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str] = mapped_column(Text, nullable=False)
    scan_status: Mapped[ScanStatus] = mapped_column(
        SCAN_STATUS_ENUM,
        nullable=False,
        default=ScanStatus.SCAN_UNAVAILABLE,
        server_default=ScanStatus.SCAN_UNAVAILABLE.value,
    )
    purge_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
