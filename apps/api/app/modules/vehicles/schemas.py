"""HTTP shapes for vehicles."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiModel
from app.modules.vehicles.models import (
    ReviewStatus,
    VehicleDocumentType,
    VehicleStatus,
    VehicleType,
)


class VehicleDocumentResponse(ApiModel):
    id: UUID
    document_type: VehicleDocumentType
    file_id: UUID
    original_name: str
    mime_type: str
    byte_size: int
    status: ReviewStatus
    uploaded_at: datetime


class VehicleResponse(ApiModel):
    id: UUID
    owner_user_id: UUID
    make: str
    model: str
    year: int
    color: str
    vehicle_type: VehicleType
    seat_capacity: int
    plate_number: str
    status: VehicleStatus
    verification_status: ReviewStatus
    documents: list[VehicleDocumentResponse]


class VehicleListResponse(ApiModel):
    items: list[VehicleResponse]


class VehicleCreateRequest(ApiModel):
    make: Annotated[str, Field(min_length=1, max_length=80)]
    model: Annotated[str, Field(min_length=1, max_length=80)]
    year: Annotated[int, Field(ge=1980, le=2100)]
    color: Annotated[str, Field(min_length=1, max_length=40)]
    vehicle_type: VehicleType
    seat_capacity: Annotated[int, Field(ge=2, le=20)]
    plate_number: Annotated[str, Field(min_length=3, max_length=20)]

    @field_validator("make", "model", "color", mode="after")
    @classmethod
    def _trim(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            msg = "must not be blank"
            raise ValueError(msg)
        return trimmed


class VehicleUpdateRequest(ApiModel):
    make: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    model: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    year: Annotated[int, Field(ge=1980, le=2100)] | None = None
    color: Annotated[str, Field(min_length=1, max_length=40)] | None = None
    vehicle_type: VehicleType | None = None
    seat_capacity: Annotated[int, Field(ge=2, le=20)] | None = None
    plate_number: Annotated[str, Field(min_length=3, max_length=20)] | None = None


class AdminVehicleListResponse(ApiModel):
    items: list[VehicleResponse]
    page: int
    page_size: int
    total_count: int
    total_pages: int


class ReviewRejectRequest(ApiModel):
    reason: Annotated[str, Field(min_length=3, max_length=1000)]
