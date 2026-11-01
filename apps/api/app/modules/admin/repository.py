"""SQL for the admin console."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz.permissions import Role
from app.modules.admin.models import AppSetting, FeatureFlag
from app.modules.audit.models import AuditLog
from app.modules.bookings.models import JoinRequestStatus, TripJoinRequest
from app.modules.safety.models import Report, ReportStatus
from app.modules.trips.models import Trip, TripStatus
from app.modules.users.models import AccountStatus, User, UserProfile, UserRole


class AdminRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @property
    def session(self) -> AsyncSession:
        return self._db

    async def search_users(
        self,
        *,
        query: str | None,
        status: AccountStatus | None,
        role: Role | None,
        page: int,
        page_size: int,
    ) -> tuple[list[User], int]:
        stmt = select(User)
        count_stmt = select(func.count()).select_from(User)
        if query:
            pattern = f"%{query.strip()}%"
            name_match = User.profile.has(UserProfile.display_name.ilike(pattern))
            email_match = User.email.ilike(pattern)
            stmt = stmt.where(or_(name_match, email_match))
            count_stmt = count_stmt.where(or_(name_match, email_match))
        if status is not None:
            stmt = stmt.where(User.status == status)
            count_stmt = count_stmt.where(User.status == status)
        if role is not None:
            role_filter = User.id.in_(select(UserRole.user_id).where(UserRole.role == role))
            stmt = stmt.where(role_filter)
            count_stmt = count_stmt.where(role_filter)
        total = int(await self._db.scalar(count_stmt) or 0)
        result = await self._db.execute(
            stmt.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_user(self, user_id: UUID) -> User | None:
        return await self._db.get(User, user_id)

    async def add_role(self, user_id: UUID, role: Role, granted_by: UUID) -> None:
        self._db.add(UserRole(user_id=user_id, role=role, granted_by=granted_by))
        await self._db.flush()

    async def remove_role(self, user_id: UUID, role: Role) -> None:
        assignment = await self._db.get(UserRole, (user_id, role))
        if assignment is not None:
            await self._db.delete(assignment)
            await self._db.flush()

    async def search_trips(
        self,
        *,
        query: str | None,
        status: TripStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[Trip, str]], int]:
        stmt = select(Trip, UserProfile.display_name).join(
            UserProfile, UserProfile.user_id == Trip.driver_id
        )
        count_stmt = select(func.count()).select_from(Trip)
        if query:
            pattern = f"%{query.strip()}%"
            filt = or_(Trip.origin_label.ilike(pattern), Trip.destination_label.ilike(pattern))
            stmt = stmt.where(filt)
            count_stmt = count_stmt.where(filt)
        if status is not None:
            stmt = stmt.where(Trip.status == status)
            count_stmt = count_stmt.where(Trip.status == status)
        total = int(await self._db.scalar(count_stmt) or 0)
        result = await self._db.execute(
            stmt.order_by(Trip.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return [(row[0], str(row[1])) for row in result.all()], total

    async def get_trip(self, trip_id: UUID) -> Trip | None:
        return await self._db.get(Trip, trip_id)

    async def list_reports(
        self, *, status: ReportStatus | None, page: int, page_size: int
    ) -> tuple[list[Report], int]:
        stmt = select(Report)
        count_stmt = select(func.count()).select_from(Report)
        if status is not None:
            stmt = stmt.where(Report.status == status)
            count_stmt = count_stmt.where(Report.status == status)
        total = int(await self._db.scalar(count_stmt) or 0)
        result = await self._db.execute(
            stmt.order_by(Report.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        return list(result.scalars()), total

    async def get_report(self, report_id: UUID) -> Report | None:
        return await self._db.get(Report, report_id)

    async def overview(self) -> dict[str, int]:
        users_total = int(await self._db.scalar(select(func.count()).select_from(User)) or 0)
        week_ago = datetime.now(UTC) - timedelta(days=7)
        users_active = int(
            await self._db.scalar(
                select(func.count()).select_from(User).where(User.last_login_at >= week_ago)
            )
            or 0
        )
        drivers = int(
            await self._db.scalar(
                select(func.count()).select_from(UserRole).where(UserRole.role == Role.DRIVER)
            )
            or 0
        )
        trips_total = int(await self._db.scalar(select(func.count()).select_from(Trip)) or 0)
        trips_completed = int(
            await self._db.scalar(
                select(func.count()).select_from(Trip).where(Trip.status == TripStatus.COMPLETED)
            )
            or 0
        )
        trips_cancelled = int(
            await self._db.scalar(
                select(func.count()).select_from(Trip).where(Trip.status == TripStatus.CANCELLED)
            )
            or 0
        )
        joins = int(await self._db.scalar(select(func.count()).select_from(TripJoinRequest)) or 0)
        matched = int(
            await self._db.scalar(
                select(func.count())
                .select_from(TripJoinRequest)
                .where(
                    TripJoinRequest.status.in_(
                        (JoinRequestStatus.ACCEPTED, JoinRequestStatus.COMPLETED)
                    )
                )
            )
            or 0
        )
        reports_open = int(
            await self._db.scalar(
                select(func.count())
                .select_from(Report)
                .where(Report.status.in_((ReportStatus.OPEN, ReportStatus.UNDER_REVIEW)))
            )
            or 0
        )
        return {
            "users_total": users_total,
            "users_active_7d": users_active,
            "drivers": drivers,
            "trips_total": trips_total,
            "trips_completed": trips_completed,
            "trips_cancelled": trips_cancelled,
            "join_requests_total": joins,
            "join_requests_matched": matched,
            "reports_open": reports_open,
        }

    async def timeseries(
        self, metric: str, start: datetime, end: datetime
    ) -> list[tuple[datetime, int]]:
        if metric == "users":
            stamp = User.created_at
            day = func.date_trunc("day", stamp)
            stmt = select(day, func.count()).where(stamp >= start, stamp < end)
        elif metric == "trips":
            stamp = Trip.created_at
            day = func.date_trunc("day", stamp)
            stmt = select(day, func.count()).where(stamp >= start, stamp < end)
        elif metric == "join_requests":
            stamp = TripJoinRequest.created_at
            day = func.date_trunc("day", stamp)
            stmt = select(day, func.count()).where(stamp >= start, stamp < end)
        elif metric == "completed_trips":
            completed = Trip.completed_at
            stmt = select(func.date_trunc("day", completed), func.count()).where(
                completed.is_not(None),
                completed >= start,
                completed < end,
                Trip.status == TripStatus.COMPLETED,
            )
            day = func.date_trunc("day", completed)
        elif metric == "cancellations":
            cancelled = Trip.cancelled_at
            stmt = select(func.date_trunc("day", cancelled), func.count()).where(
                cancelled.is_not(None),
                cancelled >= start,
                cancelled < end,
                Trip.status == TripStatus.CANCELLED,
            )
            day = func.date_trunc("day", cancelled)
        else:
            return []
        result = await self._db.execute(stmt.group_by(day).order_by(day))
        return [(row[0], int(row[1])) for row in result.all()]

    async def ensure_defaults(self) -> None:
        if await self._db.get(FeatureFlag, "ai.enabled") is None:
            self._db.add(
                FeatureFlag(
                    key="ai.enabled",
                    enabled=False,
                    description="Natural-language trip discovery and FAQ assistant.",
                )
            )
            await self._db.flush()
        for key, value in (
            ("matching.default_time_window_minutes", {"int": 60}),
            ("trips.max_passenger_seats", {"int": 7}),
            ("ratings.min_count_to_display", {"int": 3}),
            ("reports.auto_hide_threshold", {"int": 3}),
        ):
            if await self._db.get(AppSetting, key) is None:
                self._db.add(AppSetting(key=key, value=value))
                await self._db.flush()

    async def list_flags(self) -> list[FeatureFlag]:
        await self.ensure_defaults()
        result = await self._db.execute(select(FeatureFlag).order_by(FeatureFlag.key))
        return list(result.scalars())

    async def get_flag(self, key: str) -> FeatureFlag | None:
        await self.ensure_defaults()
        return await self._db.get(FeatureFlag, key)

    async def list_settings(self) -> list[AppSetting]:
        await self.ensure_defaults()
        result = await self._db.execute(select(AppSetting).order_by(AppSetting.key))
        return list(result.scalars())

    async def get_setting(self, key: str) -> AppSetting | None:
        await self.ensure_defaults()
        return await self._db.get(AppSetting, key)

    async def list_audit(
        self,
        *,
        actor_id: UUID | None,
        action: str | None,
        target_type: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog)
        count_stmt = select(func.count()).select_from(AuditLog)
        if actor_id is not None:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
            count_stmt = count_stmt.where(AuditLog.actor_id == actor_id)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
            count_stmt = count_stmt.where(AuditLog.action == action)
        if target_type is not None:
            stmt = stmt.where(AuditLog.target_type == target_type)
            count_stmt = count_stmt.where(AuditLog.target_type == target_type)
        total = int(await self._db.scalar(count_stmt) or 0)
        result = await self._db.execute(
            stmt.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars()), total
