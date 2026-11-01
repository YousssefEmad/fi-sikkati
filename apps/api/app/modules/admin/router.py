"""``/admin/*`` console (api.md §4.11)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission, Role
from app.core.authz.principal import Principal
from app.core.config import Settings, get_settings
from app.core.rate_limit import RateLimit, RateLimiter, get_rate_limiter
from app.core.security import keyed_hash
from app.modules.admin.dependencies import AdminServiceDep, request_id_of
from app.modules.admin.schemas import (
    AdminContactResponse,
    AdminModerationRequest,
    AdminReasonRequest,
    AdminReportDetailResponse,
    AdminReportListItem,
    AdminReportListResponse,
    AdminReportStatusRequest,
    AdminRolesRequest,
    AdminTripListItem,
    AdminTripListResponse,
    AdminUserDetailResponse,
    AdminUserListItem,
    AdminUserListResponse,
    AnalyticsOverviewResponse,
    AppSettingListResponse,
    AppSettingResponse,
    AppSettingUpdateRequest,
    AuditLogItem,
    AuditLogListResponse,
    FeatureFlagListResponse,
    FeatureFlagResponse,
    FeatureFlagUpdateRequest,
    TimeseriesPoint,
    TimeseriesResponse,
)
from app.modules.safety.models import ReportStatus
from app.modules.trips.models import TripStatus
from app.modules.users.models import AccountStatus, User

users_router = APIRouter(prefix="/admin/users", tags=["admin"])
trips_router = APIRouter(prefix="/admin/trips", tags=["admin"])
reports_router = APIRouter(prefix="/admin/reports", tags=["admin"])
analytics_router = APIRouter(prefix="/admin/analytics", tags=["admin"])
settings_router = APIRouter(prefix="/admin/settings", tags=["admin"])
flags_router = APIRouter(prefix="/admin/feature-flags", tags=["admin"])
audit_router = APIRouter(prefix="/admin/audit-logs", tags=["admin"])


async def _limit(
    principal: Principal,
    settings: Settings,
    limiter: RateLimiter,
) -> None:
    await limiter.enforce(
        RateLimit.parse("admin", settings.admin_rate_limit_per_user),
        keyed_hash(f"admin:{principal.user_id}", settings.auth_hash_secret.get_secret_value()),
    )


def _user_item(user: User) -> AdminUserListItem:
    return AdminUserListItem(
        id=user.id,
        display_name=user.profile.display_name,
        status=user.status,
        identity_verification_status=user.identity_verification_status,
        roles=sorted(user.role_set, key=lambda role: role.value),
        city=user.profile.city,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _user_detail(user: User) -> AdminUserDetailResponse:
    item = _user_item(user)
    return AdminUserDetailResponse(
        **item.model_dump(),
        locale=user.locale,
        email_verified=user.email_verified,
        member_since=user.created_at,
    )


@users_router.get(
    "",
    response_model=AdminUserListResponse,
    operation_id="admin_users_search",
    summary="Search accounts",
)
async def search_users(
    request: Request,
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_USERS_READ))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    q: Annotated[str | None, Query(max_length=80)] = None,
    status_filter: Annotated[AccountStatus | None, Query(alias="status")] = None,
    role: Annotated[Role | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> AdminUserListResponse:
    del request
    await _limit(principal, settings, limiter)
    rows, total, pages = await service.search_users(
        query=q, status=status_filter, role=role, page=page, page_size=page_size
    )
    return AdminUserListResponse(
        items=[_user_item(row) for row in rows],
        page=page,
        page_size=page_size,
        total_count=total,
        total_pages=pages,
    )


@users_router.get(
    "/{user_id}",
    response_model=AdminUserDetailResponse,
    operation_id="admin_users_get",
    summary="Account detail without contact PII",
)
async def get_user(
    user_id: UUID,
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_USERS_READ))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AdminUserDetailResponse:
    await _limit(principal, settings, limiter)
    return _user_detail(await service.get_user(user_id))


@users_router.get(
    "/{user_id}/contact",
    response_model=AdminContactResponse,
    operation_id="admin_users_contact",
    summary="Reveal email and phone (SUPER_ADMIN, audited)",
)
async def get_contact(
    user_id: UUID,
    request: Request,
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_PII_READ))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AdminContactResponse:
    await _limit(principal, settings, limiter)
    user = await service.get_user(user_id)
    await service.record_pii_view(
        actor_id=principal.user_id, user_id=user.id, request_id=request_id_of(request)
    )
    return AdminContactResponse(user_id=user.id, email=user.email, phone=user.phone_e164)


@users_router.post(
    "/{user_id}/suspend",
    response_model=AdminUserDetailResponse,
    operation_id="admin_users_suspend",
    summary="Suspend an account",
)
async def suspend_user(
    user_id: UUID,
    payload: AdminReasonRequest,
    request: Request,
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_USERS_MODERATE))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AdminUserDetailResponse:
    await _limit(principal, settings, limiter)
    user = await service.suspend(
        user_id,
        actor_id=principal.user_id,
        reason=payload.reason,
        request_id=request_id_of(request),
    )
    return _user_detail(user)


@users_router.post(
    "/{user_id}/restore",
    response_model=AdminUserDetailResponse,
    operation_id="admin_users_restore",
    summary="Restore a suspended account",
)
async def restore_user(
    user_id: UUID,
    payload: AdminReasonRequest,
    request: Request,
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_USERS_MODERATE))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AdminUserDetailResponse:
    await _limit(principal, settings, limiter)
    user = await service.restore(
        user_id,
        actor_id=principal.user_id,
        reason=payload.reason,
        request_id=request_id_of(request),
    )
    return _user_detail(user)


@users_router.post(
    "/{user_id}/deactivate",
    response_model=AdminUserDetailResponse,
    operation_id="admin_users_deactivate",
    summary="Permanently deactivate an account",
)
async def deactivate_user(
    user_id: UUID,
    payload: AdminReasonRequest,
    request: Request,
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_USERS_DEACTIVATE))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AdminUserDetailResponse:
    await _limit(principal, settings, limiter)
    user = await service.deactivate(
        user_id,
        actor_id=principal.user_id,
        reason=payload.reason,
        request_id=request_id_of(request),
    )
    return _user_detail(user)


@users_router.put(
    "/{user_id}/roles",
    response_model=AdminUserDetailResponse,
    operation_id="admin_users_roles",
    summary="Replace grantable roles (ADMIN/DRIVER). SUPER_ADMIN is never API-grantable.",
)
async def replace_roles(
    user_id: UUID,
    payload: AdminRolesRequest,
    request: Request,
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_ROLES_MANAGE))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AdminUserDetailResponse:
    await _limit(principal, settings, limiter)
    user = await service.replace_roles(
        user_id,
        actor_id=principal.user_id,
        roles=list(payload.roles),
        request_id=request_id_of(request),
    )
    return _user_detail(user)


@trips_router.get(
    "",
    response_model=AdminTripListResponse,
    operation_id="admin_trips_search",
    summary="Search trips",
)
async def search_trips(
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_TRIPS_READ))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    q: Annotated[str | None, Query(max_length=80)] = None,
    status_filter: Annotated[TripStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> AdminTripListResponse:
    await _limit(principal, settings, limiter)
    rows, total, pages = await service.search_trips(
        query=q, status=status_filter, page=page, page_size=page_size
    )
    items = [
        AdminTripListItem(
            id=trip.id,
            driver_id=trip.driver_id,
            driver_display_name=name,
            status=trip.status,
            origin_label=trip.origin_label,
            destination_label=trip.destination_label,
            departure_at=trip.departure_at,
            available_seats=trip.available_seats,
            total_seats=trip.total_seats,
            created_at=trip.created_at,
        )
        for trip, name in rows
    ]
    return AdminTripListResponse(
        items=items, page=page, page_size=page_size, total_count=total, total_pages=pages
    )


@reports_router.get(
    "",
    response_model=AdminReportListResponse,
    operation_id="admin_reports_list",
    summary="Moderation queue",
)
async def list_reports(
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.REPORTS_REVIEW))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    status_filter: Annotated[ReportStatus | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> AdminReportListResponse:
    await _limit(principal, settings, limiter)
    rows, total, pages = await service.list_reports(
        status=status_filter, page=page, page_size=page_size
    )
    items = [
        AdminReportListItem(
            id=row.id,
            reporter_id=row.reporter_id,
            target_type=row.target_type.value,
            target_id=row.target_id,
            reason=row.reason.value,
            status=row.status,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return AdminReportListResponse(
        items=items, page=page, page_size=page_size, total_count=total, total_pages=pages
    )


@reports_router.get(
    "/{report_id}",
    response_model=AdminReportDetailResponse,
    operation_id="admin_reports_get",
    summary="Report detail",
)
async def get_report(
    report_id: UUID,
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.REPORTS_REVIEW))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AdminReportDetailResponse:
    await _limit(principal, settings, limiter)
    row = await service.get_report(report_id)
    return AdminReportDetailResponse(
        id=row.id,
        reporter_id=row.reporter_id,
        target_type=row.target_type.value,
        target_id=row.target_id,
        reason=row.reason.value,
        status=row.status,
        created_at=row.created_at,
        description=row.description,
        resolved_by=row.resolved_by,
        resolved_at=row.resolved_at,
        resolution_notes=row.resolution_notes,
    )


@reports_router.post(
    "/{report_id}/status",
    response_model=AdminReportDetailResponse,
    operation_id="admin_reports_status",
    summary="Update report status",
)
async def set_report_status(
    report_id: UUID,
    payload: AdminReportStatusRequest,
    request: Request,
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.REPORTS_REVIEW))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AdminReportDetailResponse:
    await _limit(principal, settings, limiter)
    row = await service.set_report_status(
        report_id,
        actor_id=principal.user_id,
        status=payload.status,
        notes=payload.notes,
        request_id=request_id_of(request),
    )
    return AdminReportDetailResponse(
        id=row.id,
        reporter_id=row.reporter_id,
        target_type=row.target_type.value,
        target_id=row.target_id,
        reason=row.reason.value,
        status=row.status,
        created_at=row.created_at,
        description=row.description,
        resolved_by=row.resolved_by,
        resolved_at=row.resolved_at,
        resolution_notes=row.resolution_notes,
    )


@reports_router.post(
    "/{report_id}/actions",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="admin_reports_action",
    summary="Take a moderation action from a report",
)
async def report_action(
    report_id: UUID,
    payload: AdminModerationRequest,
    request: Request,
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.MODERATION_ACTION))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> None:
    await _limit(principal, settings, limiter)
    await service.moderate(
        report_id,
        actor_id=principal.user_id,
        target_user_id=payload.target_user_id,
        action=payload.action,
        reason=payload.reason,
        request_id=request_id_of(request),
    )


@analytics_router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    operation_id="admin_analytics_overview",
    summary="Headline counters",
)
async def analytics_overview(
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_ANALYTICS_READ))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AnalyticsOverviewResponse:
    await _limit(principal, settings, limiter)
    data = await service.overview()
    return AnalyticsOverviewResponse(**data)


@analytics_router.get(
    "/timeseries",
    response_model=TimeseriesResponse,
    operation_id="admin_analytics_timeseries",
    summary="Daily counts for a metric",
)
async def analytics_timeseries(
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_ANALYTICS_READ))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    metric: Annotated[str, Query()],
    start: Annotated[datetime, Query(alias="from")],
    end: Annotated[datetime, Query(alias="to")],
) -> TimeseriesResponse:
    await _limit(principal, settings, limiter)
    points = await service.timeseries(metric, start, end)
    return TimeseriesResponse(
        metric=metric,
        items=[TimeseriesPoint(day=day, count=count) for day, count in points],
    )


@settings_router.get(
    "",
    response_model=AppSettingListResponse,
    operation_id="admin_settings_list",
    summary="Editable configuration keys",
)
async def list_settings(
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_SETTINGS_READ))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AppSettingListResponse:
    await _limit(principal, settings, limiter)
    rows = await service.list_settings()
    return AppSettingListResponse(
        items=[
            AppSettingResponse(key=row.key, value=row.value, updated_at=row.updated_at)
            for row in rows
        ]
    )


@settings_router.put(
    "/{key}",
    response_model=AppSettingResponse,
    operation_id="admin_settings_update",
    summary="Update a configuration value",
)
async def update_setting(
    key: str,
    payload: AppSettingUpdateRequest,
    request: Request,
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_SETTINGS_WRITE))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AppSettingResponse:
    await _limit(principal, settings, limiter)
    row = await service.set_setting(
        key, value=payload.value, actor_id=principal.user_id, request_id=request_id_of(request)
    )
    return AppSettingResponse(key=row.key, value=row.value, updated_at=row.updated_at)


@flags_router.get(
    "",
    response_model=FeatureFlagListResponse,
    operation_id="admin_flags_list",
    summary="Feature flags",
)
async def list_flags(
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_FLAGS_MANAGE))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> FeatureFlagListResponse:
    await _limit(principal, settings, limiter)
    rows = await service.list_flags()
    return FeatureFlagListResponse(
        items=[
            FeatureFlagResponse(
                key=row.key,
                enabled=row.enabled,
                description=row.description,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
    )


@flags_router.put(
    "/{key}",
    response_model=FeatureFlagResponse,
    operation_id="admin_flags_update",
    summary="Enable or disable a flag",
)
async def update_flag(
    key: str,
    payload: FeatureFlagUpdateRequest,
    request: Request,
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_FLAGS_MANAGE))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> FeatureFlagResponse:
    await _limit(principal, settings, limiter)
    row = await service.set_flag(
        key, enabled=payload.enabled, actor_id=principal.user_id, request_id=request_id_of(request)
    )
    return FeatureFlagResponse(
        key=row.key, enabled=row.enabled, description=row.description, updated_at=row.updated_at
    )


@audit_router.get(
    "",
    response_model=AuditLogListResponse,
    operation_id="admin_audit_list",
    summary="Read-only audit log",
)
async def list_audit(
    service: AdminServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.ADMIN_AUDIT_READ))],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    actor_id: Annotated[UUID | None, Query(alias="actorId")] = None,
    action: Annotated[str | None, Query()] = None,
    target_type: Annotated[str | None, Query(alias="targetType")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> AuditLogListResponse:
    await _limit(principal, settings, limiter)
    rows, total, pages = await service.list_audit(
        actor_id=actor_id, action=action, target_type=target_type, page=page, page_size=page_size
    )
    return AuditLogListResponse(
        items=[
            AuditLogItem(
                id=row.id,
                actor_type=row.actor_type.value,
                actor_id=row.actor_id,
                action=row.action,
                target_type=row.target_type,
                target_id=row.target_id,
                created_at=row.created_at,
            )
            for row in rows
        ],
        page=page,
        page_size=page_size,
        total_count=total,
        total_pages=pages,
    )
