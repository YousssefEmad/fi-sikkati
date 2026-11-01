"""Phone alerts via the Web Push protocol.

The browser (or the installed home-screen app) shows the alert even when Fi Sikkati
is not open. The payload is a title, a sentence, and a link — never a name or a
message body.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import structlog
from pywebpush import WebPushException, webpush_async

from app.core.config import Settings
from app.modules.notifications.emails import notification_text
from app.modules.notifications.links import notification_link
from app.modules.notifications.models import NotificationType
from app.modules.notifications.repository import NotificationRepository

log = structlog.get_logger("app.notifications.push")

_GONE = frozenset({404, 410})
_HOLD_SECONDS = 60 * 60 * 24


def push_configured(settings: Settings) -> bool:
    return bool(settings.vapid_public_key and settings.vapid_private_key.get_secret_value())


async def deliver_phone_alerts(
    repository: NotificationRepository,
    settings: Settings,
    pending: list[tuple[UUID, UUID, NotificationType, dict[str, Any]]],
) -> None:
    """Send one phone alert per written notification. ``pending`` is (user, id, type, payload)."""
    if not pending or not push_configured(settings):
        return
    user_ids = tuple({user_id for user_id, _id, _type, _payload in pending})
    locales = await repository.locales_for(user_ids)
    by_user: dict[UUID, list[Any]] = {}
    for row in await repository.subscriptions_for(user_ids):
        by_user.setdefault(row.user_id, []).append(row)
    private_key = settings.vapid_private_key.get_secret_value()
    subject = settings.vapid_subject
    for user_id, notification_id, type_, payload in pending:
        devices = by_user.get(user_id)
        if not devices:
            continue
        title, body = notification_text(type_, locales.get(user_id, "ar"))
        url = notification_link(
            str(settings.public_web_url), locales.get(user_id, "ar"), type_, payload
        )
        message = {
            "title": title,
            "body": body,
            "url": url,
            "tag": str(notification_id),
        }
        for device in devices:
            await _send_one(
                repository,
                endpoint=device.endpoint,
                p256dh=device.p256dh,
                auth=device.auth,
                message=message,
                private_key=private_key,
                subject=subject,
            )


async def _send_one(
    repository: NotificationRepository,
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
    message: dict[str, str],
    private_key: str,
    subject: str,
) -> None:
    try:
        await webpush_async(
            subscription_info={"endpoint": endpoint, "keys": {"p256dh": p256dh, "auth": auth}},
            data=json.dumps(message),
            vapid_private_key=private_key,
            vapid_claims={"sub": subject},
            ttl=_HOLD_SECONDS,
        )
    except WebPushException as exc:
        if exc.status_code in _GONE:
            await repository.delete_endpoint(endpoint)
            return
        log.warning("phone_alert_failed", status=exc.status_code)
    except Exception as exc:
        log.warning("phone_alert_failed", error=type(exc).__name__)
