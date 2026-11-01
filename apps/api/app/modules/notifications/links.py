"""Where a notification should open. Identifiers only; no names."""

from __future__ import annotations

from typing import Any

from app.modules.notifications.models import NotificationType

_PATHS: dict[NotificationType, str] = {
    NotificationType.NEW_MESSAGE: "/messages/{conversationId}",
    NotificationType.TRIP_STARTED: "/messages/{conversationId}",
    NotificationType.VERIFICATION_STATUS_CHANGED: "/me/verification",
    NotificationType.REPORT_UPDATED: "/me/safety",
    NotificationType.RATING_RECEIVED: "/trips/{tripId}",
    NotificationType.ACCOUNT_MODERATED: "/me/safety",
    NotificationType.ANNOUNCEMENT: "/me/notifications",
    NotificationType.JOIN_REQUEST_RECEIVED: "/trips/{tripId}?request={requestId}",
    NotificationType.JOIN_REQUEST_ACCEPTED: "/trips/{tripId}",
    NotificationType.JOIN_REQUEST_CANCELLED: "/trips/{tripId}",
    NotificationType.JOIN_REQUEST_REJECTED: "/search",
    NotificationType.TRIP_CANCELLED: "/search",
    NotificationType.TRIP_UPDATED: "/trips/{tripId}",
    NotificationType.TRIP_COMPLETED: "/trips/{tripId}",
    NotificationType.TRIP_REMINDER: "/trips/{tripId}",
    NotificationType.TRIP_STARTING_SOON: "/trips/{tripId}",
}


def notification_link(
    base: str, locale: str, type_: NotificationType, payload: dict[str, Any]
) -> str:
    root = f"{base.rstrip('/')}/{locale}"
    if type_ is NotificationType.REVIEW_REQUESTED:
        kind = str(payload.get("kind", "")).lower()
        if kind == "report":
            return f"{root}/admin/reports"
        user_id = payload.get("userId")
        if user_id and kind in {"identity", "driver", "vehicle"}:
            vehicle_id = payload.get("vehicleId")
            vehicle = f"&vehicle={vehicle_id}" if vehicle_id else ""
            return f"{root}/admin/verifications?user={user_id}&kind={kind}{vehicle}"
        return f"{root}/admin/verifications"
    template = _PATHS.get(type_)
    if template is None:
        trip_id = payload.get("tripId")
        return f"{root}/trips/{trip_id}" if trip_id else f"{root}/home"
    path = template
    for key, value in payload.items():
        path = path.replace("{" + key + "}", str(value))
    if "{" in path:
        trip_id = payload.get("tripId")
        return f"{root}/trips/{trip_id}" if trip_id else f"{root}/home"
    return f"{root}{path}"
