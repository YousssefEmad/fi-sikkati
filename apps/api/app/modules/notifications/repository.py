"""SQL for notifications and preferences."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz.permissions import Role
from app.core.ids import uuid7
from app.modules.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationPreference,
    NotificationType,
    PushSubscription,
)
from app.modules.trips.models import Trip, TripStatus
from app.modules.users.models import AccountStatus, User, UserProfile, UserRole


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @property
    def session(self) -> AsyncSession:
        return self._db

    async def insert(
        self,
        *,
        user_id: UUID,
        type_: NotificationType,
        payload: dict[str, Any],
        email_requested_at: datetime | None,
        dedupe_key: str | None,
    ) -> Notification | None:
        """Insert one row; ``None`` when ``dedupe_key`` already exists for the user."""
        row = Notification(
            id=uuid7(),
            user_id=user_id,
            type=type_,
            payload=payload,
            email_requested_at=email_requested_at,
            dedupe_key=dedupe_key,
        )
        try:
            async with self._db.begin_nested():
                self._db.add(row)
                await self._db.flush()
        except IntegrityError:
            return None
        return row

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        before: tuple[datetime, UUID] | None,
        limit: int,
        unread_only: bool,
    ) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        if before is not None:
            created_at, ident = before
            query = query.where(
                (Notification.created_at < created_at)
                | ((Notification.created_at == created_at) & (Notification.id < ident))
            )
        query = query.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
        result = await self._db.execute(query)
        return list(result.scalars())

    async def active_staff_ids(self) -> tuple[UUID, ...]:
        """Active ADMIN and SUPER_ADMIN accounts. A person with both roles is listed once."""
        result = await self._db.execute(
            select(UserRole.user_id)
            .join(User, User.id == UserRole.user_id)
            .where(
                UserRole.role.in_((Role.ADMIN, Role.SUPER_ADMIN)),
                User.status == AccountStatus.ACTIVE,
            )
            .distinct()
        )
        return tuple(result.scalars())

    async def unread_count(self, user_id: UUID) -> int:
        value = await self._db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
        )
        return int(value or 0)

    async def mark_read(self, user_id: UUID, *, ids: Sequence[UUID] | None, now: datetime) -> int:
        statement = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=now)
        )
        if ids is not None:
            statement = statement.where(Notification.id.in_(tuple(ids)))
        result = await self._db.execute(statement)
        return int(result.rowcount or 0) if isinstance(result, CursorResult) else 0

    async def clear_all(self, user_id: UUID) -> int:
        result = await self._db.execute(
            delete(Notification).where(Notification.user_id == user_id)
        )
        return int(result.rowcount or 0) if isinstance(result, CursorResult) else 0

    async def preferences(self, user_id: UUID) -> list[NotificationPreference]:
        result = await self._db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        return list(result.scalars())

    async def preference_map(
        self, user_ids: Iterable[UUID]
    ) -> dict[tuple[UUID, NotificationType, NotificationChannel], bool]:
        ids = tuple(user_ids)
        if not ids:
            return {}
        result = await self._db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id.in_(ids))
        )
        return {(row.user_id, row.type, row.channel): row.enabled for row in result.scalars()}

    async def upsert_preference(
        self,
        user_id: UUID,
        *,
        type_: NotificationType,
        channel: NotificationChannel,
        enabled: bool,
    ) -> None:
        statement = (
            insert(NotificationPreference)
            .values(user_id=user_id, type=type_, channel=channel, enabled=enabled)
            .on_conflict_do_update(
                index_elements=["user_id", "type", "channel"],
                set_={"enabled": enabled, "updated_at": func.now()},
            )
        )
        await self._db.execute(statement)

    async def pending_emails(self, limit: int) -> list[Notification]:
        result = await self._db.execute(
            select(Notification)
            .where(
                Notification.email_requested_at.is_not(None),
                Notification.email_sent_at.is_(None),
            )
            .order_by(Notification.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return list(result.scalars())

    async def mark_email_sent(self, notification: Notification, now: datetime) -> None:
        notification.email_sent_at = now

    async def upcoming_trips(
        self, *, not_before: datetime, not_after: datetime
    ) -> list[tuple[UUID, UUID]]:
        """Published/full trips whose departure is in ``[not_before, not_after]``."""
        result = await self._db.execute(
            select(Trip.id, Trip.driver_id).where(
                Trip.status.in_((TripStatus.PUBLISHED, TripStatus.FULL)),
                Trip.departure_at >= not_before,
                Trip.departure_at <= not_after,
            )
        )
        return [(row[0], row[1]) for row in result]

    async def recipients(self, user_ids: Iterable[UUID]) -> dict[UUID, tuple[str, str, str, bool]]:
        """``user_id → (email, display name, locale, account is active)``."""
        ids = tuple(user_ids)
        if not ids:
            return {}
        result = await self._db.execute(
            select(User.id, User.email, UserProfile.display_name, User.locale, User.status)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(User.id.in_(ids))
        )
        return {
            row[0]: (str(row[1]), str(row[2]), str(row[3]), str(row[4]) == "ACTIVE")
            for row in result
        }

    async def locales_for(self, user_ids: Iterable[UUID]) -> dict[UUID, str]:
        ids = tuple(user_ids)
        if not ids:
            return {}
        result = await self._db.execute(select(User.id, User.locale).where(User.id.in_(ids)))
        return {row[0]: str(row[1]) for row in result}

    async def subscriptions_for(self, user_ids: Iterable[UUID]) -> list[PushSubscription]:
        ids = tuple(user_ids)
        if not ids:
            return []
        result = await self._db.execute(
            select(PushSubscription).where(PushSubscription.user_id.in_(ids))
        )
        return list(result.scalars())

    async def upsert_subscription(
        self, *, user_id: UUID, endpoint: str, p256dh: str, auth: str, now: datetime
    ) -> None:
        statement = (
            insert(PushSubscription)
            .values(
                id=uuid7(),
                user_id=user_id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_push_subscriptions_endpoint",
                set_={
                    "user_id": user_id,
                    "p256dh": p256dh,
                    "auth": auth,
                    "updated_at": now,
                },
            )
        )
        await self._db.execute(statement)

    async def delete_subscription(self, *, user_id: UUID, endpoint: str) -> None:
        await self._db.execute(
            delete(PushSubscription).where(
                PushSubscription.user_id == user_id,
                PushSubscription.endpoint == endpoint,
            )
        )

    async def delete_endpoint(self, endpoint: str) -> None:
        await self._db.execute(
            delete(PushSubscription).where(PushSubscription.endpoint == endpoint)
        )
