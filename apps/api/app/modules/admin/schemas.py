"""HTTP shapes for the admin platform (api.md §4.11)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import Field

from app.core.authz.permissions import Role
from app.core.schemas import ApiModel
from app.modules.safety.models import ModerationActionType, ReportStatus
from app.modules.trips.models import TripStatus
from app.modules.users.models import AccountStatus, IdentityVerificationStatus

Reason = Annotated[str, Field(min_length=8, max_length=500)]


class AdminUserListItem(ApiModel):
    id: UUID
    display_name: str
    status: AccountStatus
    identity_verification_status: IdentityVerificationStatus
    roles: list[Role]
    city: str | None
    created_at: datetime
    last_login_at: datetime | None


class AdminUserListResponse(ApiModel):
    items: list[AdminUserListItem]
    page: int
    page_size: int
    total_count: int
    total_pages: int


class AdminUserDetailResponse(AdminUserListItem):
    locale: str
    email_verified: bool
    member_since: datetime


class AdminContactResponse(ApiModel):
    user_id: UUID
    email: str
    phone: str | None


class AdminReasonRequest(ApiModel):
    reason: Reason


class AdminRolesRequest(ApiModel):
    roles: list[Literal["ADMIN", "DRIVER"]]


class AdminTripListItem(ApiModel):
    id: UUID
    driver_id: UUID
    driver_display_name: str
    status: TripStatus
    origin_label: str
    destination_label: str
    departure_at: datetime
    available_seats: int
    total_seats: int
    created_at: datetime


class AdminTripListResponse(ApiModel):
    items: list[AdminTripListItem]
    page: int
    page_size: int
    total_count: int
    total_pages: int


class AdminReportListItem(ApiModel):
    id: UUID
    reporter_id: UUID
    target_type: str
    target_id: UUID
    reason: str
    status: ReportStatus
    created_at: datetime


class AdminReportListResponse(ApiModel):
    items: list[AdminReportListItem]
    page: int
    page_size: int
    total_count: int
    total_pages: int


class AdminReportDetailResponse(AdminReportListItem):
    description: str | None
    resolved_by: UUID | None
    resolved_at: datetime | None
    resolution_notes: str | None


class AdminReportStatusRequest(ApiModel):
    status: ReportStatus
    notes: Annotated[str, Field(min_length=4, max_length=1000)] | None = None


class AdminModerationRequest(ApiModel):
    action: ModerationActionType
    reason: Reason
    target_user_id: UUID


class AnalyticsOverviewResponse(ApiModel):
    users_total: int
    users_active_7d: int
    drivers: int
    trips_total: int
    trips_completed: int
    trips_cancelled: int
    join_requests_total: int
    join_requests_matched: int
    reports_open: int


class TimeseriesPoint(ApiModel):
    day: datetime
    count: int


class TimeseriesResponse(ApiModel):
    metric: str
    items: list[TimeseriesPoint]


class FeatureFlagResponse(ApiModel):
    key: str
    enabled: bool
    description: str
    updated_at: datetime


class FeatureFlagListResponse(ApiModel):
    items: list[FeatureFlagResponse]


class FeatureFlagUpdateRequest(ApiModel):
    enabled: bool


class AppSettingResponse(ApiModel):
    key: str
    value: dict[str, Any]
    updated_at: datetime


class AppSettingListResponse(ApiModel):
    items: list[AppSettingResponse]


class AppSettingUpdateRequest(ApiModel):
    value: dict[str, Any]


class AuditLogItem(ApiModel):
    id: UUID
    actor_type: str
    actor_id: UUID | None
    action: str
    target_type: str | None
    target_id: UUID | None
    created_at: datetime


class AuditLogListResponse(ApiModel):
    items: list[AuditLogItem]
    page: int
    page_size: int
    total_count: int
    total_pages: int
