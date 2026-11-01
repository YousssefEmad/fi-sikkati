"""Notification rules (BR-NOTIF-01..05).

* Every notification is written in-app first; email is a second channel decided per user
  preference and sent by the worker *after* the originating transaction committed.
* Payloads carry identifiers only. The web client resolves names and labels itself with the
  recipient's own permissions, so a notification can never show more than its reader may see.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.email import EmailSender
from app.core.errors import ValidationAppError
from app.core.events import (
    AnnouncementPublished,
    DomainEvent,
    JoinRequestAccepted,
    JoinRequestCancelled,
    JoinRequestCreated,
    JoinRequestRejected,
    MessagePosted,
    RatingSubmitted,
    ReportStatusChanged,
    ReviewRequested,
    TripCancelled,
    TripCompleted,
    TripStarted,
    TripUpdated,
    UserModerated,
    VerificationStatusChanged,
)
from app.modules.notifications.emails import notification_email
from app.modules.notifications.links import notification_link
from app.modules.notifications.models import (
    EMAIL_DEFAULT_ON,
    SAFETY_CRITICAL,
    Notification,
    NotificationChannel,
    NotificationType,
)
from app.modules.notifications.push import deliver_phone_alerts
from app.modules.notifications.repository import NotificationRepository

log = structlog.get_logger("app.notifications")

_MAX_MARK_READ = 200


@dataclass(frozen=True, slots=True)
class NotificationView:
    id: UUID
    type: NotificationType
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class PreferenceView:
    type: NotificationType
    channel: NotificationChannel
    enabled: bool
    locked: bool


def default_enabled(type_: NotificationType, channel: NotificationChannel) -> bool:
    if channel is NotificationChannel.IN_APP:
        return True
    return type_ in EMAIL_DEFAULT_ON


class NotificationService:
    def __init__(self, repository: NotificationRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    # --- writing -------------------------------------------------------------------------

    async def notify(
        self,
        user_ids: tuple[UUID, ...] | list[UUID],
        type_: NotificationType,
        payload: dict[str, Any],
        *,
        dedupe_key: str | None = None,
        now: datetime | None = None,
    ) -> int:
        """Write one notification per recipient, honouring preferences. Returns rows written."""
        recipients = tuple(dict.fromkeys(user_ids))
        if not recipients:
            return 0
        moment = now or datetime.now(UTC)
        preferences = await self._repository.preference_map(recipients)
        written = 0
        pending_push: list[tuple[UUID, UUID, NotificationType, dict[str, Any]]] = []
        for user_id in recipients:
            in_app = preferences.get((user_id, type_, NotificationChannel.IN_APP))
            if in_app is False and type_ not in SAFETY_CRITICAL:
                continue
            email = preferences.get((user_id, type_, NotificationChannel.EMAIL))
            wants_email = (
                default_enabled(type_, NotificationChannel.EMAIL) if email is None else email
            )
            row = await self._repository.insert(
                user_id=user_id,
                type_=type_,
                payload=payload,
                email_requested_at=moment if wants_email else None,
                dedupe_key=dedupe_key,
            )
            if row is not None:
                written += 1
                pending_push.append((user_id, row.id, type_, payload))
        if written:
            log.info("notifications_written", type=type_.value, count=written)
        if pending_push:
            await deliver_phone_alerts(self._repository, self._settings, pending_push)
        return written

    async def handle_event(self, event: DomainEvent) -> None:  # noqa: PLR0912
        """Fan a domain event out to the people it concerns (business-rules.md §6)."""
        match event:
            case JoinRequestCreated():
                await self.notify(
                    (event.driver_id,),
                    NotificationType.JOIN_REQUEST_RECEIVED,
                    {"tripId": str(event.trip_id), "requestId": str(event.request_id)},
                )
            case JoinRequestAccepted():
                await self.notify(
                    (event.passenger_id,),
                    NotificationType.JOIN_REQUEST_ACCEPTED,
                    {"tripId": str(event.trip_id), "requestId": str(event.request_id)},
                )
            case JoinRequestRejected():
                await self.notify(
                    (event.passenger_id,),
                    NotificationType.JOIN_REQUEST_REJECTED,
                    {"tripId": str(event.trip_id), "requestId": str(event.request_id)},
                )
            case JoinRequestCancelled():
                await self.notify(
                    (event.driver_id,),
                    NotificationType.JOIN_REQUEST_CANCELLED,
                    {
                        "tripId": str(event.trip_id),
                        "requestId": str(event.request_id),
                        "wasAccepted": event.was_accepted,
                    },
                )
            case TripUpdated():
                await self.notify(
                    event.passenger_ids,
                    NotificationType.TRIP_UPDATED,
                    {"tripId": str(event.trip_id)},
                )
            case TripStarted():
                await self.notify(
                    event.passenger_ids,
                    NotificationType.TRIP_STARTED,
                    {"tripId": str(event.trip_id)},
                )
            case TripCancelled():
                recipients = event.passenger_ids
                if event.cancelled_by != "DRIVER":
                    recipients = (*recipients, event.driver_id)
                await self.notify(
                    recipients,
                    NotificationType.TRIP_CANCELLED,
                    {"tripId": str(event.trip_id), "cancelledBy": event.cancelled_by},
                )
            case TripCompleted():
                await self.notify(
                    (*event.passenger_ids, event.driver_id),
                    NotificationType.TRIP_COMPLETED,
                    {"tripId": str(event.trip_id)},
                )
            case MessagePosted():
                payload = {
                    "conversationId": str(event.conversation_id),
                    "messageId": str(event.message_id),
                }
                if event.trip_id is not None:
                    payload["tripId"] = str(event.trip_id)
                await self.notify(event.recipient_ids, NotificationType.NEW_MESSAGE, payload)
            case VerificationStatusChanged():
                await self.notify(
                    (event.user_id,),
                    NotificationType.VERIFICATION_STATUS_CHANGED,
                    {"kind": event.kind, "status": event.status},
                )
            case RatingSubmitted():
                await self.notify(
                    (event.ratee_id,),
                    NotificationType.RATING_RECEIVED,
                    {"tripId": str(event.trip_id)},
                )
            case ReportStatusChanged():
                await self.notify(
                    (event.reporter_id,),
                    NotificationType.REPORT_UPDATED,
                    {"reportId": str(event.report_id), "status": event.status},
                )
            case UserModerated():
                await self.notify(
                    (event.user_id,),
                    NotificationType.ACCOUNT_MODERATED,
                    {"action": event.action},
                )
            case ReviewRequested():
                # Every admin and super admin, including a staff member who applied themselves.
                staff = await self._repository.active_staff_ids()
                payload: dict[str, Any] = {
                    "kind": event.kind,
                    "userId": str(event.subject_user_id),
                }
                if event.report_id is not None:
                    payload["reportId"] = str(event.report_id)
                if event.vehicle_id is not None:
                    payload["vehicleId"] = str(event.vehicle_id)
                await self.notify(staff, NotificationType.REVIEW_REQUESTED, payload)
            case AnnouncementPublished():
                # Fan-out to every active account happens in the worker (``announce``), not
                # inline: an announcement to thousands of users must not block the admin.
                return
            case _:
                return

    # --- reading -------------------------------------------------------------------------

    async def list_inbox(
        self,
        user_id: UUID,
        *,
        before: tuple[datetime, UUID] | None,
        limit: int,
        unread_only: bool,
    ) -> list[NotificationView]:
        rows = await self._repository.list_for_user(
            user_id, before=before, limit=limit, unread_only=unread_only
        )
        return [_view(row) for row in rows]

    async def unread_count(self, user_id: UUID) -> int:
        return await self._repository.unread_count(user_id)

    async def mark_read(self, user_id: UUID, *, ids: Sequence[UUID] | None) -> int:
        if ids is not None and len(ids) > _MAX_MARK_READ:
            raise ValidationAppError(f"Mark at most {_MAX_MARK_READ} notifications per call.")
        return await self._repository.mark_read(user_id, ids=ids, now=datetime.now(UTC))

    async def preferences(self, user_id: UUID) -> list[PreferenceView]:
        stored = {
            (row.type, row.channel): row.enabled
            for row in await self._repository.preferences(user_id)
        }
        views: list[PreferenceView] = []
        for type_ in NotificationType:
            for channel in NotificationChannel:
                locked = channel is NotificationChannel.IN_APP and type_ in SAFETY_CRITICAL
                enabled = stored.get((type_, channel), default_enabled(type_, channel))
                views.append(
                    PreferenceView(
                        type=type_,
                        channel=channel,
                        enabled=True if locked else enabled,
                        locked=locked,
                    )
                )
        return views

    async def update_preferences(
        self,
        user_id: UUID,
        changes: Sequence[tuple[NotificationType, NotificationChannel, bool]],
    ) -> list[PreferenceView]:
        for type_, channel, enabled in changes:
            if channel is NotificationChannel.IN_APP and type_ in SAFETY_CRITICAL and not enabled:
                raise ValidationAppError(
                    f"{type_.value} is safety-critical and cannot be turned off in-app."
                )
            await self._repository.upsert_preference(
                user_id, type_=type_, channel=channel, enabled=enabled
            )
        return await self.preferences(user_id)

    # --- email delivery (worker) ---------------------------------------------------------

    async def send_trip_cadence(self, *, now: datetime | None = None) -> dict[str, int]:
        """BR-NOTIF-04: 24h reminder and 2h starting-soon, once per trip per recipient."""
        moment = now or datetime.now(UTC)
        reminder_from = moment + timedelta(
            hours=self._settings.notifications_trip_reminder_hours, minutes=-15
        )
        reminder_to = moment + timedelta(hours=self._settings.notifications_trip_reminder_hours)
        soon_from = moment + timedelta(
            minutes=self._settings.notifications_starting_soon_minutes - 15
        )
        soon_to = moment + timedelta(minutes=self._settings.notifications_starting_soon_minutes)
        reminder_trips = await self._repository.upcoming_trips(
            not_before=reminder_from, not_after=reminder_to
        )
        soon_trips = await self._repository.upcoming_trips(not_before=soon_from, not_after=soon_to)
        reminded = starting = 0
        # Passengers are resolved through join requests in SQL by the bookings table; we
        # keep this query local by notifying the driver here and letting a second pass
        # (the worker) include accepted passengers via payload-only trip ids.
        for trip_id, driver_id in reminder_trips:
            reminded += await self.notify(
                (driver_id,),
                NotificationType.TRIP_REMINDER,
                {"tripId": str(trip_id)},
                dedupe_key=f"TRIP_REMINDER:{trip_id}",
                now=moment,
            )
        for trip_id, driver_id in soon_trips:
            starting += await self.notify(
                (driver_id,),
                NotificationType.TRIP_STARTING_SOON,
                {"tripId": str(trip_id)},
                dedupe_key=f"TRIP_STARTING_SOON:{trip_id}",
                now=moment,
            )
        return {"reminders": reminded, "startingSoon": starting}

    async def dispatch_pending_emails(self, sender: EmailSender) -> int:
        """Send queued emails. Runs in the worker; each batch is one transaction."""
        rows = await self._repository.pending_emails(self._settings.notifications_email_batch_size)
        if not rows:
            return 0
        people = await self._repository.recipients({row.user_id for row in rows})
        now = datetime.now(UTC)
        sent = 0
        for row in rows:
            person = people.get(row.user_id)
            # Inactive accounts never receive mail; mark as handled so the queue drains.
            if person is not None and person[3]:
                email, display_name, locale, _active = person
                message = notification_email(
                    to=email,
                    display_name=display_name,
                    locale=locale,
                    type_=row.type,
                    link=notification_link(
                        str(self._settings.public_web_url), locale, row.type, row.payload
                    ),
                )
                try:
                    await sender.send(message)
                    sent += 1
                except Exception:
                    log.exception("notification_email_failed", notification_id=str(row.id))
                    continue
            await self._repository.mark_email_sent(row, now)
        return sent


def _view(row: Notification) -> NotificationView:
    return NotificationView(
        id=row.id,
        type=row.type,
        payload=dict(row.payload),
        read_at=row.read_at,
        created_at=row.created_at,
    )

    async def save_push_subscription(
        self, user_id: UUID, *, endpoint: str, p256dh: str, auth: str
    ) -> None:
        await self._repository.upsert_subscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            now=datetime.now(UTC),
        )

    async def remove_push_subscription(self, user_id: UUID, *, endpoint: str) -> None:
        await self._repository.delete_subscription(user_id=user_id, endpoint=endpoint)


def notification_service_for(db: AsyncSession, settings: Settings) -> NotificationService:
    return NotificationService(NotificationRepository(db), settings)
