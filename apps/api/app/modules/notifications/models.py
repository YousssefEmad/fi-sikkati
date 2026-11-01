"""``notifications`` and ``notification_preferences`` (database.md §2.6)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Final
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, TimestampMixin, uuid_primary_key


class NotificationType(StrEnum):
    JOIN_REQUEST_RECEIVED = "JOIN_REQUEST_RECEIVED"
    JOIN_REQUEST_ACCEPTED = "JOIN_REQUEST_ACCEPTED"
    JOIN_REQUEST_REJECTED = "JOIN_REQUEST_REJECTED"
    JOIN_REQUEST_CANCELLED = "JOIN_REQUEST_CANCELLED"
    TRIP_UPDATED = "TRIP_UPDATED"
    TRIP_STARTED = "TRIP_STARTED"
    TRIP_CANCELLED = "TRIP_CANCELLED"
    TRIP_COMPLETED = "TRIP_COMPLETED"
    TRIP_STARTING_SOON = "TRIP_STARTING_SOON"
    TRIP_REMINDER = "TRIP_REMINDER"
    NEW_MESSAGE = "NEW_MESSAGE"
    NEW_MATCHING_TRIP = "NEW_MATCHING_TRIP"
    VERIFICATION_STATUS_CHANGED = "VERIFICATION_STATUS_CHANGED"
    RATING_RECEIVED = "RATING_RECEIVED"
    REPORT_UPDATED = "REPORT_UPDATED"
    ACCOUNT_MODERATED = "ACCOUNT_MODERATED"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    # A staff member must review something before it can proceed.
    REVIEW_REQUESTED = "REVIEW_REQUESTED"


class NotificationChannel(StrEnum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


#: BR-NOTIF-03: safety-critical types cannot be muted in-app.
SAFETY_CRITICAL: Final[frozenset[NotificationType]] = frozenset(
    {
        NotificationType.TRIP_CANCELLED,
        NotificationType.ACCOUNT_MODERATED,
        NotificationType.TRIP_STARTING_SOON,
        NotificationType.REVIEW_REQUESTED,
    }
)

#: Types that send an email by default when the user has not chosen otherwise.
EMAIL_DEFAULT_ON: Final[frozenset[NotificationType]] = frozenset(
    {
        NotificationType.JOIN_REQUEST_RECEIVED,
        NotificationType.JOIN_REQUEST_ACCEPTED,
        NotificationType.JOIN_REQUEST_REJECTED,
        NotificationType.TRIP_CANCELLED,
        NotificationType.TRIP_REMINDER,
        NotificationType.VERIFICATION_STATUS_CHANGED,
        NotificationType.ACCOUNT_MODERATED,
        NotificationType.REPORT_UPDATED,
        NotificationType.REVIEW_REQUESTED,
    }
)


def _pg_enum(enum: type[StrEnum], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda members: [m.value for m in members])


NOTIFICATION_TYPE_ENUM: Final = _pg_enum(NotificationType, "notifications_type_enum")
NOTIFICATION_CHANNEL_ENUM: Final = _pg_enum(
    NotificationChannel, "notification_preferences_channel_enum"
)


class Notification(Base, CreatedAtMixin):
    """One in-app notification. ``payload`` holds identifiers only (security.md §4)."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_created", "user_id", "created_at"),
        Index(
            "ix_notifications_user_unread",
            "user_id",
            postgresql_where=text("read_at IS NULL"),
        ),
        Index(
            "ix_notifications_email_pending",
            "created_at",
            postgresql_where=text("email_requested_at IS NOT NULL AND email_sent_at IS NULL"),
        ),
        Index(
            "uq_notifications_dedupe_key",
            "user_id",
            "dedupe_key",
            unique=True,
            postgresql_where=text("dedupe_key IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(NOTIFICATION_TYPE_ENUM, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set when the user's preference asked for an email; cleared to ``sent`` by the worker.
    email_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Idempotency for scheduled notifications (reminders): ``<type>:<trip id>``.
    dedupe_key: Mapped[str | None] = mapped_column(Text, nullable=True)


class NotificationPreference(Base, TimestampMixin):
    """Per user, per type, per channel on/off. Missing row ⇒ the documented default."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    type: Mapped[NotificationType] = mapped_column(NOTIFICATION_TYPE_ENUM, primary_key=True)
    channel: Mapped[NotificationChannel] = mapped_column(
        NOTIFICATION_CHANNEL_ENUM, primary_key=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PushSubscription(Base, TimestampMixin):
    """A browser push endpoint for one signed-in device."""

    __tablename__ = "push_subscriptions"
    __table_args__ = (
        Index("ix_push_subscriptions_user_id", "user_id"),
        UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),
    )

    id: Mapped[UUID] = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    p256dh: Mapped[str] = mapped_column(Text, nullable=False)
    auth: Mapped[str] = mapped_column(Text, nullable=False)
