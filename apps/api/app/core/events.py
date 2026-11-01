"""In-process domain events (architecture.md §3.4).

Trips, bookings and verification *emit* facts; notifications, chat and analytics *react*.
The emitting module never imports the reacting one — ``app.main`` subscribes handlers on a
:class:`EventDispatcher` and binds it on ``app.state``. Handlers run inside the emitting
request's unit of work, so a notification row is committed exactly when the change it
describes is, and rolled back with it.

Events carry identifiers only (no names, no message bodies): every consumer loads what it
needs itself, and nothing here can leak PII into logs.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import UUID

import structlog
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger("app.events")


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=_now)

    @property
    def name(self) -> str:
        return type(self).__name__


# --- trips -------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class TripPublished(DomainEvent):
    trip_id: UUID
    driver_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class TripUpdated(DomainEvent):
    trip_id: UUID
    driver_id: UUID
    passenger_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class TripStarted(DomainEvent):
    trip_id: UUID
    driver_id: UUID
    passenger_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class TripCompleted(DomainEvent):
    trip_id: UUID
    driver_id: UUID
    passenger_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class TripCancelled(DomainEvent):
    trip_id: UUID
    driver_id: UUID
    passenger_ids: tuple[UUID, ...]
    cancelled_by: str
    reason: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class TripExpired(DomainEvent):
    trip_id: UUID
    driver_id: UUID


# --- bookings ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class JoinRequestCreated(DomainEvent):
    request_id: UUID
    trip_id: UUID
    driver_id: UUID
    passenger_id: UUID
    seats: int


@dataclass(frozen=True, slots=True, kw_only=True)
class JoinRequestAccepted(DomainEvent):
    request_id: UUID
    trip_id: UUID
    driver_id: UUID
    passenger_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class JoinRequestRejected(DomainEvent):
    request_id: UUID
    trip_id: UUID
    driver_id: UUID
    passenger_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class JoinRequestCancelled(DomainEvent):
    request_id: UUID
    trip_id: UUID
    driver_id: UUID
    passenger_id: UUID
    was_accepted: bool


# --- verification ------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class VerificationStatusChanged(DomainEvent):
    user_id: UUID
    kind: str  # "IDENTITY" | "DRIVER"
    status: str  # "APPROVED" | "REJECTED"


@dataclass(frozen=True, slots=True, kw_only=True)
class ReviewRequested(DomainEvent):
    """Someone is waiting on a person: identity, driver, vehicle, or a safety report."""

    kind: str  # "IDENTITY" | "DRIVER" | "VEHICLE" | "REPORT"
    subject_user_id: UUID
    report_id: UUID | None = None
    vehicle_id: UUID | None = None


# --- chat --------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class MessagePosted(DomainEvent):
    conversation_id: UUID
    trip_id: UUID | None = None
    message_id: UUID
    sender_id: UUID
    recipient_ids: tuple[UUID, ...]


# --- safety ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class RatingSubmitted(DomainEvent):
    trip_id: UUID
    rater_id: UUID
    ratee_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportStatusChanged(DomainEvent):
    report_id: UUID
    reporter_id: UUID
    status: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UserModerated(DomainEvent):
    """An administrator acted on an account (warning, suspension, restore, driver revoked)."""

    user_id: UUID
    action: str
    actor_id: UUID


# --- platform ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class AnnouncementPublished(DomainEvent):
    announcement_id: UUID
    author_id: UUID


# --- dispatcher --------------------------------------------------------------------------

E = TypeVar("E", bound=DomainEvent)
Handler = Callable[[AsyncSession, Any], Awaitable[None]]


class EventDispatcher:
    """Routes events to the handlers subscribed for their type. Built once at startup."""

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)
        self._catch_all: list[Handler] = []

    def subscribe(
        self, event_type: type[E], handler: Callable[[AsyncSession, E], Awaitable[None]]
    ) -> None:
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        """Receive every event (analytics)."""
        self._catch_all.append(handler)

    async def dispatch(self, db: AsyncSession, event: DomainEvent) -> None:
        handlers = [*self._handlers.get(type(event), ()), *self._catch_all]
        for handler in handlers:
            await handler(db, event)
        log.debug("event_dispatched", kind=event.name, handlers=len(handlers))


class EventPublisher:
    """A dispatcher bound to one unit of work; this is what services receive."""

    def __init__(self, dispatcher: EventDispatcher | None, db: AsyncSession) -> None:
        self._dispatcher = dispatcher
        self._db = db

    async def publish(self, event: DomainEvent) -> None:
        if self._dispatcher is None:
            return
        await self._dispatcher.dispatch(self._db, event)


class NoopEventPublisher(EventPublisher):
    def __init__(self) -> None:
        self._dispatcher = None
        self._db = None  # type: ignore[assignment]

    async def publish(self, event: DomainEvent) -> None:
        del event


_ATTR = "event_dispatcher"


def bind_event_dispatcher(app_state: object, dispatcher: EventDispatcher) -> None:
    setattr(app_state, _ATTR, dispatcher)


def get_event_dispatcher(request: Request) -> EventDispatcher | None:
    found = getattr(request.app.state, _ATTR, None)
    return found if isinstance(found, EventDispatcher) else None


def event_publisher_for(request: Request, db: AsyncSession) -> EventPublisher:
    return EventPublisher(get_event_dispatcher(request), db)
