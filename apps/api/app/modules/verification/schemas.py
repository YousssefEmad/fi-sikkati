"""HTTP shapes for verification."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiModel
from app.modules.users.models import IdentityVerificationStatus
from app.modules.verification.models import (
    DriverVerificationStatus,
    IdentityDocumentType,
    ReviewStatus,
)


class IdentityDocumentResponse(ApiModel):
    id: UUID
    document_type: IdentityDocumentType
    file_id: UUID
    original_name: str
    mime_type: str
    byte_size: int
    status: ReviewStatus
    uploaded_at: datetime


class DriverStatusResponse(ApiModel):
    status: DriverVerificationStatus | None
    licence_expires_on: date | None
    licence_file_id: UUID | None
    licence_original_name: str | None
    vehicle_id: UUID | None
    rejection_reason: str | None
    submitted_at: datetime | None


class VerificationStatusResponse(ApiModel):
    identity_status: IdentityVerificationStatus
    identity_documents: list[IdentityDocumentResponse]
    identity_rejection_reason: str | None
    review_sla_hours: int
    driver: DriverStatusResponse


class DriverSubmitRequest(ApiModel):
    vehicle_id: UUID
    licence_expires_on: date
    licence_file_id: UUID


class ReviewRejectRequest(ApiModel):
    reason: Annotated[str, Field(min_length=3, max_length=1000)]


class LicenceUploadResponse(ApiModel):
    file_id: UUID
    original_name: str
    mime_type: str
    byte_size: int


class AdminIdentityQueueItem(ApiModel):
    user_id: UUID
    display_name: str
    email: str
    submitted_at: datetime
    document_count: int


class VehicleRegistrationRequest(ApiModel):
    vehicle_id: UUID


class AdminDriverQueueItem(ApiModel):
    user_id: UUID
    verification_id: UUID
    display_name: str
    email: str
    submitted_at: datetime
    vehicle_id: UUID
    licence_expires_on: date


class AdminIdentityQueueResponse(ApiModel):
    items: list[AdminIdentityQueueItem]
    page: int
    page_size: int
    total_count: int
    total_pages: int


class AdminDriverQueueResponse(ApiModel):
    items: list[AdminDriverQueueItem]
    page: int
    page_size: int
    total_count: int
    total_pages: int
