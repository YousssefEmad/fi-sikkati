"""Bodies for ``/me/notifications`` and ``/me/notification-preferences`` (api.md §4.9)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiModel
from app.modules.notifications.models import NotificationChannel, NotificationType


class NotificationResponse(ApiModel):
    id: UUID
    type: NotificationType
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(ApiModel):
    items: list[NotificationResponse]
    next_cursor: str | None


class UnreadCountResponse(ApiModel):
    unread: int


class MarkReadRequest(ApiModel):
    """Omit ``ids`` (or send ``null``) to mark everything read."""

    ids: list[UUID] | None = Field(default=None, max_length=200)


class MarkReadResponse(ApiModel):
    marked: int


class ClearNotificationsResponse(ApiModel):
    deleted: int


class PushSubscriptionRequest(ApiModel):
    endpoint: str = Field(min_length=8, max_length=2000)
    p256dh: str = Field(min_length=8, max_length=200)
    auth: str = Field(min_length=8, max_length=200)


class PushSubscriptionResponse(ApiModel):
    enabled: bool


class PreferenceItem(ApiModel):
    type: NotificationType
    channel: NotificationChannel
    enabled: bool
    locked: bool = False


class PreferencesResponse(ApiModel):
    items: list[PreferenceItem]


class PreferenceChange(ApiModel):
    type: NotificationType
    channel: NotificationChannel
    enabled: bool


class PreferencesUpdateRequest(ApiModel):
    items: list[PreferenceChange] = Field(min_length=1, max_length=100)
