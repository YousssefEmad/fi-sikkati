"""Admin operations (FR-ADM-01..08). Community ADMIN vs platform SUPER_ADMIN."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

from app.core.authz.permissions import Role
from app.core.authz.ports import SessionRevoker
from app.core.errors import ForbiddenError, NotFoundError, ValidationAppError
from app.core.events import EventPublisher, NoopEventPublisher, UserModerated
from app.core.ids import uuid7
from app.modules.admin.models import AI_FLAG_KEY, AppSetting, FeatureFlag
from app.modules.admin.repository import AdminRepository
from app.modules.audit.models import ActorType, AuditAction, AuditLog
from app.modules.audit.service import AuditLogWriter
from app.modules.safety.models import (
    ModerationAction,
    ModerationActionType,
    Report,
    ReportStatus,
)
from app.modules.trips.models import Trip, TripStatus
from app.modules.users.models import AccountStatus, User

EDITABLE_SETTINGS = frozenset(
    {
        "matching.default_time_window_minutes",
        "trips.max_passenger_seats",
        "ratings.min_count_to_display",
        "reports.auto_hide_threshold",
    }
)
TIMESERIES_METRICS = frozenset(
    {"users", "trips", "join_requests", "completed_trips", "cancellations"}
)


class AdminService:
    def __init__(
        self,
        repository: AdminRepository,
        *,
        audit: AuditLogWriter,
        events: EventPublisher | None = None,
        revoker: SessionRevoker | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._events = events or NoopEventPublisher()
        self._revoker = revoker

    async def search_users(
        self,
        *,
        query: str | None,
        status: AccountStatus | None,
        role: Role | None,
        page: int,
        page_size: int,
    ) -> tuple[list[User], int, int]:
        rows, total = await self._repository.search_users(
            query=query, status=status, role=role, page=page, page_size=page_size
        )
        return rows, total, _pages(total, page_size)

    async def get_user(self, user_id: UUID) -> User:
        user = await self._repository.get_user(user_id)
        if user is None or user.status is AccountStatus.DELETED:
            raise NotFoundError("User not found.")
        return user

    async def suspend(
        self, user_id: UUID, *, actor_id: UUID, reason: str, request_id: str | None
    ) -> User:
        user = await self._require_moderatable(user_id, actor_id)
        if user.status is AccountStatus.SUSPENDED:
            return user
        user.status = AccountStatus.SUSPENDED
        await self._after_moderation(
            user, actor_id, AuditAction.USER_SUSPENDED, "SUSPEND_USER", reason, request_id
        )
        if self._revoker is not None:
            await self._revoker(self._repository.session, user.id, "suspended")
        return user

    async def restore(
        self, user_id: UUID, *, actor_id: UUID, reason: str, request_id: str | None
    ) -> User:
        user = await self._require_moderatable(user_id, actor_id)
        if user.status is not AccountStatus.SUSPENDED:
            raise ValidationAppError("Only a suspended account can be restored.")
        user.status = AccountStatus.ACTIVE
        await self._after_moderation(
            user, actor_id, AuditAction.USER_RESTORED, "RESTORE_USER", reason, request_id
        )
        return user

    async def deactivate(
        self, user_id: UUID, *, actor_id: UUID, reason: str, request_id: str | None
    ) -> User:
        user = await self._require_moderatable(user_id, actor_id)
        user.status = AccountStatus.DEACTIVATED
        await self._after_moderation(
            user, actor_id, AuditAction.USER_DEACTIVATED, "SUSPEND_USER", reason, request_id
        )
        if self._revoker is not None:
            await self._revoker(self._repository.session, user.id, "deactivated")
        return user

    async def replace_roles(
        self, user_id: UUID, *, actor_id: UUID, roles: list[str], request_id: str | None
    ) -> User:
        user = await self._require_moderatable(user_id, actor_id)
        wanted = {Role(item) for item in roles}
        if Role.SUPER_ADMIN in wanted:
            raise ForbiddenError("SUPER_ADMIN cannot be granted through the API.")
        current = set(user.role_set)
        keep = {Role.PASSENGER, Role.SUPER_ADMIN} & current
        next_roles = keep | wanted
        for extra in current - next_roles:
            if extra is Role.SUPER_ADMIN:
                raise ForbiddenError("SUPER_ADMIN cannot be revoked through the API.")
            await self._repository.remove_role(user.id, extra)
            await self._audit.record(
                AuditAction.ROLE_REVOKED,
                actor_type=ActorType.ADMIN,
                actor_id=actor_id,
                target_type="user",
                target_id=user.id,
                request_id=request_id,
                metadata={"role": extra.value},
            )
        for missing in next_roles - current:
            await self._repository.add_role(user.id, missing, actor_id)
            await self._audit.record(
                AuditAction.ROLE_GRANTED,
                actor_type=ActorType.ADMIN,
                actor_id=actor_id,
                target_type="user",
                target_id=user.id,
                request_id=request_id,
                metadata={"role": missing.value},
            )
        await self._repository.session.refresh(user)
        return user

    async def search_trips(
        self,
        *,
        query: str | None,
        status: TripStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[Trip, str]], int, int]:
        rows, total = await self._repository.search_trips(
            query=query, status=status, page=page, page_size=page_size
        )
        return rows, total, _pages(total, page_size)

    async def list_reports(
        self, *, status: ReportStatus | None, page: int, page_size: int
    ) -> tuple[list[Report], int, int]:
        rows, total = await self._repository.list_reports(
            status=status, page=page, page_size=page_size
        )
        return rows, total, _pages(total, page_size)

    async def get_report(self, report_id: UUID) -> Report:
        report = await self._repository.get_report(report_id)
        if report is None:
            raise NotFoundError("Report not found.")
        return report

    async def set_report_status(
        self,
        report_id: UUID,
        *,
        actor_id: UUID,
        status: ReportStatus,
        notes: str | None,
        request_id: str | None,
    ) -> Report:
        report = await self._repository.get_report(report_id)
        if report is None:
            raise NotFoundError("Report not found.")
        report.status = status
        if status in {ReportStatus.RESOLVED, ReportStatus.DISMISSED}:
            report.resolved_by = actor_id
            report.resolved_at = datetime.now(UTC)
            report.resolution_notes = notes
        await self._audit.record(
            AuditAction.REPORT_STATUS_CHANGED,
            actor_type=ActorType.ADMIN,
            actor_id=actor_id,
            target_type="report",
            target_id=report.id,
            request_id=request_id,
            metadata={"status": status.value},
        )
        return report

    async def moderate(
        self,
        report_id: UUID | None,
        *,
        actor_id: UUID,
        target_user_id: UUID,
        action: ModerationActionType,
        reason: str,
        request_id: str | None,
    ) -> None:
        target = await self._require_moderatable(target_user_id, actor_id)
        if action is ModerationActionType.SUSPEND_USER:
            await self.suspend(target.id, actor_id=actor_id, reason=reason, request_id=request_id)
        elif action is ModerationActionType.RESTORE_USER:
            await self.restore(target.id, actor_id=actor_id, reason=reason, request_id=request_id)
        self._repository.session.add(
            ModerationAction(
                id=uuid7(),
                report_id=report_id,
                actor_id=actor_id,
                target_user_id=target.id,
                action=action,
                reason=reason,
            )
        )
        await self._audit.record(
            AuditAction.MODERATION_ACTION,
            actor_type=ActorType.ADMIN,
            actor_id=actor_id,
            target_type="user",
            target_id=target.id,
            request_id=request_id,
            metadata={"action": action.value},
        )
        await self._events.publish(
            UserModerated(user_id=target.id, action=action.value, actor_id=actor_id)
        )

    async def overview(self) -> dict[str, int]:
        return await self._repository.overview()

    async def timeseries(
        self, metric: str, start: datetime, end: datetime
    ) -> list[tuple[datetime, int]]:
        if metric not in TIMESERIES_METRICS:
            raise ValidationAppError("Unknown analytics metric.")
        if end <= start:
            raise ValidationAppError("to must be after from.")
        return await self._repository.timeseries(metric, start, end)

    async def list_flags(self) -> list[FeatureFlag]:
        return await self._repository.list_flags()

    async def set_flag(
        self, key: str, *, enabled: bool, actor_id: UUID, request_id: str | None
    ) -> FeatureFlag:
        flag = await self._repository.get_flag(key)
        if flag is None:
            raise NotFoundError("Feature flag not found.")
        flag.enabled = enabled
        flag.updated_by = actor_id
        await self._repository.session.flush()
        await self._repository.session.refresh(flag)
        await self._audit.record(
            AuditAction.FEATURE_FLAG_CHANGED,
            actor_type=ActorType.ADMIN,
            actor_id=actor_id,
            target_type="feature_flag",
            request_id=request_id,
            metadata={"key": key, "enabled": enabled},
        )
        return flag

    async def list_settings(self) -> list[AppSetting]:
        return await self._repository.list_settings()

    async def set_setting(
        self, key: str, *, value: dict[str, object], actor_id: UUID, request_id: str | None
    ) -> AppSetting:
        if key not in EDITABLE_SETTINGS:
            raise ValidationAppError("This setting is not editable.")
        setting = await self._repository.get_setting(key)
        if setting is None:
            raise NotFoundError("Setting not found.")
        setting.value = value
        setting.updated_by = actor_id
        await self._repository.session.flush()
        await self._repository.session.refresh(setting)
        await self._audit.record(
            AuditAction.SETTINGS_CHANGED,
            actor_type=ActorType.ADMIN,
            actor_id=actor_id,
            target_type="app_setting",
            request_id=request_id,
            metadata={"key": key},
        )
        return setting

    async def list_audit(
        self,
        *,
        actor_id: UUID | None,
        action: str | None,
        target_type: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AuditLog], int, int]:
        rows, total = await self._repository.list_audit(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            page=page,
            page_size=page_size,
        )
        return rows, total, _pages(total, page_size)

    async def flag_enabled(self, key: str = AI_FLAG_KEY) -> bool | None:
        flag = await self._repository.get_flag(key)
        return None if flag is None else flag.enabled

    async def record_pii_view(
        self, *, actor_id: UUID, user_id: UUID, request_id: str | None
    ) -> None:
        await self._audit.record(
            AuditAction.ADMIN_PII_VIEWED,
            actor_type=ActorType.ADMIN,
            actor_id=actor_id,
            target_type="user",
            target_id=user_id,
            request_id=request_id,
        )

    async def _require_moderatable(self, user_id: UUID, actor_id: UUID) -> User:
        if user_id == actor_id:
            raise ForbiddenError("You cannot moderate your own account.")
        user = await self.get_user(user_id)
        if Role.SUPER_ADMIN in user.role_set:
            raise ForbiddenError("SUPER_ADMIN accounts cannot be moderated through the API.")
        return user

    async def _after_moderation(
        self,
        user: User,
        actor_id: UUID,
        audit: AuditAction,
        action: str,
        reason: str,
        request_id: str | None,
    ) -> None:
        await self._audit.record(
            audit,
            actor_type=ActorType.ADMIN,
            actor_id=actor_id,
            target_type="user",
            target_id=user.id,
            request_id=request_id,
            metadata={"reason": reason[:80]},
        )
        await self._events.publish(UserModerated(user_id=user.id, action=action, actor_id=actor_id))


def _pages(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / page_size)) if total else 1
