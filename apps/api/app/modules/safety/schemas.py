"""Bodies for ratings, reports and blocks (api.md §4.10)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiModel
from app.modules.safety.models import ReportReason, ReportStatus, ReportTargetType


class RatingCreate(ApiModel):
    ratee_id: UUID
    overall: Annotated[int, Field(ge=1, le=5)]
    punctuality: Annotated[int, Field(ge=1, le=5)] | None = None
    communication: Annotated[int, Field(ge=1, le=5)] | None = None
    experience: Annotated[int, Field(ge=1, le=5)] | None = None
    comment: Annotated[str, Field(max_length=500)] | None = None


class RatingResponse(ApiModel):
    id: UUID
    trip_id: UUID
    rater_id: UUID
    ratee_id: UUID
    overall: int
    punctuality: int | None
    communication: int | None
    experience: int | None
    comment: str | None
    created_at: datetime


class RatingSummaryResponse(ApiModel):
    user_id: UUID
    count: int
    average: float | None
    visible: bool


class ReportCreate(ApiModel):
    target_type: ReportTargetType
    target_id: UUID
    reason: ReportReason
    description: Annotated[str, Field(max_length=1000)] | None = None


class ReportResponse(ApiModel):
    id: UUID
    reporter_id: UUID
    target_type: ReportTargetType
    target_id: UUID
    reason: ReportReason
    description: str | None
    status: ReportStatus
    created_at: datetime
    resolved_at: datetime | None


class ReportListResponse(ApiModel):
    items: list[ReportResponse]
    next_cursor: str | None


class BlockCreate(ApiModel):
    user_id: UUID


class BlockResponse(ApiModel):
    user_id: UUID
    display_name: str
    created_at: datetime


class BlockListResponse(ApiModel):
    items: list[BlockResponse]
