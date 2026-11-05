"""``/me/notifications`` and ``/me/notification-preferences`` (api.md §4.9)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission
from app.core.authz.principal import Principal
from app.core.pagination import decode_cursor, encode_cursor
from app.modules.notifications.dependencies import NotificationServiceDep
from app.modules.notifications.schemas import (
    ClearNotificationsResponse,
    MarkReadRequest,
    MarkReadResponse,
    NotificationListResponse,
    NotificationResponse,
    PreferenceItem,
    PreferencesResponse,
    PreferencesUpdateRequest,
    PushSubscriptionRequest,
    PushSubscriptionResponse,
    UnreadCountResponse,
)
from app.modules.notifications.service import NotificationView

router = APIRouter(prefix="/me/notifications", tags=["notifications"])
preferences_router = APIRouter(prefix="/me/notification-preferences", tags=["notifications"])


def _response(view: NotificationView) -> NotificationResponse:
    return NotificationResponse(
        id=view.id,
        type=view.type,
        payload=view.payload,
        read_at=view.read_at,
        created_at=view.created_at,
    )


@router.get(
    "",
    response_model=NotificationListResponse,
    operation_id="notifications_list",
    summary="The signed-in user's notifications, newest first",
)
async def list_notifications(
    service: NotificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.NOTIFICATIONS_READ))],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    unread_only: Annotated[bool, Query(alias="unreadOnly")] = False,
) -> NotificationListResponse:
    rows = await service.list_inbox(
        principal.user_id, before=decode_cursor(cursor), limit=limit + 1, unread_only=unread_only
    )
    page = rows[:limit]
    next_cursor = None
    if len(rows) > limit and page:
        next_cursor = encode_cursor(page[-1].created_at, page[-1].id)
    return NotificationListResponse(items=[_response(row) for row in page], next_cursor=next_cursor)


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    operation_id="notifications_unread_count",
    summary="How many notifications are unread",
)
async def unread_count(
    service: NotificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.NOTIFICATIONS_READ))],
) -> UnreadCountResponse:
    return UnreadCountResponse(unread=await service.unread_count(principal.user_id))


@router.post(
    "/read",
    response_model=MarkReadResponse,
    operation_id="notifications_mark_read",
    summary="Mark notifications as read",
)
async def mark_read(
    payload: MarkReadRequest,
    service: NotificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.NOTIFICATIONS_MANAGE))],
) -> MarkReadResponse:
    return MarkReadResponse(marked=await service.mark_read(principal.user_id, ids=payload.ids))


@router.delete(
    "",
    response_model=ClearNotificationsResponse,
    operation_id="notifications_clear_all",
    summary="Delete every notification for the signed-in user",
)
async def clear_all_notifications(
    service: NotificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.NOTIFICATIONS_MANAGE))],
) -> ClearNotificationsResponse:
    return ClearNotificationsResponse(deleted=await service.clear_all(principal.user_id))


@preferences_router.get(
    "",
    response_model=PreferencesResponse,
    operation_id="notification_preferences_get",
    summary="Notification preferences per type and channel",
)
async def get_preferences(
    service: NotificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.NOTIFICATIONS_READ))],
) -> PreferencesResponse:
    items = await service.preferences(principal.user_id)
    return PreferencesResponse(
        items=[
            PreferenceItem(type=i.type, channel=i.channel, enabled=i.enabled, locked=i.locked)
            for i in items
        ]
    )


@preferences_router.put(
    "",
    response_model=PreferencesResponse,
    operation_id="notification_preferences_update",
    summary="Update notification preferences",
)
async def update_preferences(
    payload: PreferencesUpdateRequest,
    service: NotificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.NOTIFICATIONS_MANAGE))],
) -> PreferencesResponse:
    items = await service.update_preferences(
        principal.user_id, [(i.type, i.channel, i.enabled) for i in payload.items]
    )
    return PreferencesResponse(
        items=[
            PreferenceItem(type=i.type, channel=i.channel, enabled=i.enabled, locked=i.locked)
            for i in items
        ]
    )


push_router = APIRouter(prefix="/me/push-subscriptions", tags=["notifications"])


@push_router.put(
    "",
    response_model=PushSubscriptionResponse,
    operation_id="push_subscribe",
    summary="Register this device for phone alerts",
)
async def subscribe_push(
    payload: PushSubscriptionRequest,
    service: NotificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.NOTIFICATIONS_MANAGE))],
) -> PushSubscriptionResponse:
    await service.save_push_subscription(
        principal.user_id, endpoint=payload.endpoint, p256dh=payload.p256dh, auth=payload.auth
    )
    return PushSubscriptionResponse(enabled=True)


@push_router.delete(
    "",
    status_code=204,
    operation_id="push_unsubscribe",
    summary="Stop phone alerts on this device",
)
async def unsubscribe_push(
    payload: PushSubscriptionRequest,
    service: NotificationServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.NOTIFICATIONS_MANAGE))],
) -> None:
    await service.remove_push_subscription(principal.user_id, endpoint=payload.endpoint)
