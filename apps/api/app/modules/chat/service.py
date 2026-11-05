"""Trip chat rules (BR-CHAT-01..07).

Conversation is created when the trip is published. The driver is a member from the start;
accepted passengers join on accept and leave (but keep history) on cancel/reject. After the
trip is cancelled, or 24 hours after completion, the thread is read-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import (
    ConversationReadOnlyError,
    ForbiddenError,
    NotFoundError,
    ValidationAppError,
)
from app.core.events import (
    DomainEvent,
    EventPublisher,
    JoinRequestAccepted,
    JoinRequestCancelled,
    MessagePosted,
    NoopEventPublisher,
    TripCancelled,
    TripCompleted,
    TripPublished,
    TripStarted,
    TripUpdated,
)
from app.core.ids import uuid7
from app.core.lifecycle import BlockChecker, NoopBlockChecker
from app.core.rate_limit import RateLimit, RateLimiter
from app.core.security import keyed_hash
from app.modules.chat.models import (
    MESSAGE_MAX_LENGTH,
    Conversation,
    ConversationType,
    Message,
    MessageKind,
    SystemEvent,
)
from app.modules.chat.repository import ChatRepository

log = structlog.get_logger("app.chat")

_SYSTEM_COPY: dict[SystemEvent, dict[str, str]] = {
    SystemEvent.CONVERSATION_OPENED: {
        "ar": "فُتحت محادثة هذه الرحلة.",
        "en": "This trip's conversation is open.",
    },
    SystemEvent.PASSENGER_JOINED: {
        "ar": "انضم راكب إلى المحادثة.",
        "en": "A passenger joined the conversation.",
    },
    SystemEvent.PASSENGER_LEFT: {
        "ar": "غادر راكب المحادثة.",
        "en": "A passenger left the conversation.",
    },
    SystemEvent.TRIP_UPDATED: {
        "ar": "عدّل السائق تفاصيل الرحلة.",
        "en": "The driver updated the trip details.",
    },
    SystemEvent.TRIP_STARTED: {
        "ar": "بدأت الرحلة.",
        "en": "The trip has started.",
    },
    SystemEvent.TRIP_CANCELLED: {
        "ar": "أُلغيت الرحلة. المحادثة للقراءة فقط.",
        "en": "The trip was cancelled. This conversation is now read-only.",
    },
    SystemEvent.TRIP_COMPLETED: {
        "ar": "اكتملت الرحلة. تبقى المحادثة مفتوحة ليوم واحد.",
        "en": "The trip is complete. Chat stays open for one more day.",
    },
    SystemEvent.CONVERSATION_CLOSED: {
        "ar": "أُغلقت المحادثة.",
        "en": "This conversation is closed.",
    },
}


@dataclass(frozen=True, slots=True)
class MessageView:
    id: UUID
    conversation_id: UUID
    sender_id: UUID | None
    sender_display_name: str | None
    kind: MessageKind
    body: str
    system_event: str | None
    created_at: datetime
    deleted: bool


@dataclass(frozen=True, slots=True)
class ConversationView:
    id: UUID
    trip_id: UUID | None
    origin_label: str | None
    destination_label: str | None
    departure_at: datetime | None
    is_read_only: bool
    unread_count: int
    muted: bool
    last_message: MessageView | None
    member_ids: tuple[UUID, ...]
    member_names: tuple[str, ...]


class ChatService:
    def __init__(
        self,
        repository: ChatRepository,
        settings: Settings,
        *,
        events: EventPublisher | None = None,
        blocks: BlockChecker | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._events = events or NoopEventPublisher()
        self._blocks = blocks or NoopBlockChecker()
        self._limiter = limiter

    async def handle_event(self, event: DomainEvent) -> None:
        match event:
            case TripPublished():
                await self.open_for_trip(event.trip_id, driver_id=event.driver_id)
            case JoinRequestAccepted():
                await self.add_passenger(event.trip_id, event.passenger_id)
            case JoinRequestCancelled() if event.was_accepted:
                await self.remove_passenger(event.trip_id, event.passenger_id)
            case TripUpdated():
                await self.system(event.trip_id, SystemEvent.TRIP_UPDATED)
            case TripStarted():
                await self.system(event.trip_id, SystemEvent.TRIP_STARTED)
            case TripCancelled():
                await self.system(event.trip_id, SystemEvent.TRIP_CANCELLED, close=True)
                await self.purge_trip_conversation(event.trip_id)
            case TripCompleted():
                await self.system(event.trip_id, SystemEvent.TRIP_COMPLETED)
                await self.purge_trip_conversation(event.trip_id)
            case _:
                return

    async def open_for_trip(self, trip_id: UUID, *, driver_id: UUID) -> Conversation:
        existing = await self._repository.get_for_trip(trip_id)
        if existing is not None:
            return existing
        conversation = await self._repository.create_trip_conversation(trip_id)
        now = datetime.now(UTC)
        await self._repository.add_member(conversation.id, driver_id, now=now)
        await self._system_message(conversation.id, SystemEvent.CONVERSATION_OPENED)
        log.info("conversation_opened", trip_id=str(trip_id), conversation_id=str(conversation.id))
        return conversation

    async def add_passenger(self, trip_id: UUID, passenger_id: UUID) -> None:
        conversation = await self._repository.get_for_trip(trip_id)
        if conversation is None:
            trip = await self._repository.get_trip(trip_id)
            if trip is None:
                return
            conversation = await self.open_for_trip(trip_id, driver_id=trip.driver_id)
        await self._repository.add_member(conversation.id, passenger_id, now=datetime.now(UTC))
        await self._system_message(conversation.id, SystemEvent.PASSENGER_JOINED)

    async def remove_passenger(self, trip_id: UUID, passenger_id: UUID) -> None:
        conversation = await self._repository.get_for_trip(trip_id)
        if conversation is None:
            return
        await self._repository.leave(conversation.id, passenger_id, now=datetime.now(UTC))
        await self._system_message(conversation.id, SystemEvent.PASSENGER_LEFT)

    async def system(self, trip_id: UUID, event: SystemEvent, *, close: bool = False) -> None:
        conversation = await self._repository.get_for_trip(trip_id)
        if conversation is None:
            return
        await self._system_message(conversation.id, event)
        if close:
            await self._repository.set_read_only(conversation, True)

    async def list_mine(
        self, user_id: UUID, *, before: tuple[datetime, UUID] | None, limit: int
    ) -> list[ConversationView]:
        await self._join_community(user_id)
        rows = await self._repository.list_for_user(user_id, before=before, limit=limit)
        return [await self._conversation_view(row, viewer_id=user_id) for row in rows]

    async def get(
        self, conversation_id: UUID, *, viewer_id: UUID, is_admin: bool
    ) -> ConversationView:
        conversation = await self._require_member(conversation_id, viewer_id, is_admin=is_admin)
        return await self._conversation_view(conversation, viewer_id=viewer_id)

    async def list_messages(
        self,
        conversation_id: UUID,
        *,
        viewer_id: UUID,
        is_admin: bool,
        before_id: UUID | None,
        limit: int,
    ) -> list[MessageView]:
        await self._require_member(conversation_id, viewer_id, is_admin=is_admin)
        rows = await self._repository.list_messages(
            conversation_id, before_id=before_id, limit=limit, include_deleted=is_admin
        )
        return await self._message_views(rows)

    async def post(
        self,
        conversation_id: UUID,
        *,
        sender_id: UUID,
        body: str,
        client_message_id: UUID,
        hash_secret: str,
    ) -> MessageView:
        conversation = await self._require_member(conversation_id, sender_id, is_admin=False)
        if conversation.is_read_only:
            raise ConversationReadOnlyError("This conversation is closed.")
        if conversation.type is not ConversationType.COMMUNITY:
            hidden = await self._blocks.hidden_user_ids(self._repository.session, sender_id)
            members = await self._repository.active_member_ids(conversation_id)
            if any(member in hidden for member in members if member != sender_id):
                raise ConversationReadOnlyError("This conversation is closed.")
        else:
            members = await self._repository.active_member_ids(conversation_id)
        cleaned = _body(body, self._settings.chat_message_max_length)
        if self._limiter is not None:
            limit = RateLimit.parse("chat", self._settings.chat_rate_limit_per_user)
            await self._limiter.enforce(limit, keyed_hash(str(sender_id), hash_secret))
        existing = await self._repository.get_by_client_id(sender_id, client_message_id)
        if existing is not None:
            views = await self._message_views([existing])
            return views[0]
        message = Message(
            id=uuid7(),
            conversation_id=conversation_id,
            sender_id=sender_id,
            kind=MessageKind.TEXT,
            body=cleaned,
            client_message_id=client_message_id,
        )
        try:
            await self._repository.insert_message(message)
        except IntegrityError:
            recovered = await self._repository.get_by_client_id(sender_id, client_message_id)
            if recovered is None:
                raise
            views = await self._message_views([recovered])
            return views[0]
        await self._repository.mark_read(conversation_id, sender_id, message.id)
        notify_members = await self._repository.active_notify_member_ids(conversation_id)
        recipients = tuple(user for user in notify_members if user != sender_id)
        if recipients:
            await self._events.publish(
                MessagePosted(
                    conversation_id=conversation_id,
                    trip_id=conversation.trip_id,
                    message_id=message.id,
                    sender_id=sender_id,
                    recipient_ids=recipients,
                )
            )
        views = await self._message_views([message])
        return views[0]

    async def mark_read(
        self, conversation_id: UUID, *, viewer_id: UUID, message_id: UUID | None
    ) -> None:
        await self._require_member(conversation_id, viewer_id, is_admin=False)
        target = message_id
        if target is None:
            last = await self._repository.last_message(conversation_id)
            if last is None:
                return
            target = last.id
        await self._repository.mark_read(conversation_id, viewer_id, target)

    async def remove_message(
        self,
        message_id: UUID,
        *,
        actor_id: UUID,
        is_admin: bool,
        conversation_id: UUID | None = None,
    ) -> MessageView:
        message = await self._repository.get_message(message_id)
        if message is None:
            raise NotFoundError("Message not found.")
        if conversation_id is not None and message.conversation_id != conversation_id:
            raise NotFoundError("Message not found.")
        if not is_admin and message.sender_id != actor_id:
            raise ForbiddenError("You cannot remove this message.")
        if message.deleted_at is None:
            await self._repository.soft_delete(message, actor_id=actor_id, now=datetime.now(UTC))
        views = await self._message_views([message])
        return views[0]

    async def remove_messages(
        self,
        conversation_id: UUID,
        message_ids: list[UUID],
        *,
        actor_id: UUID,
        is_admin: bool,
    ) -> int:
        if not is_admin:
            raise ForbiddenError("Only moderators can remove multiple messages.")
        await self._require_member(conversation_id, actor_id, is_admin=True)
        return await self._repository.soft_delete_ids(
            conversation_id,
            message_ids,
            actor_id=actor_id,
            now=datetime.now(UTC),
        )

    async def clear_conversation(
        self, conversation_id: UUID, *, actor_id: UUID, is_admin: bool
    ) -> int:
        if not is_admin:
            raise ForbiddenError("Only moderators can clear a conversation.")
        await self._require_member(conversation_id, actor_id, is_admin=True)
        return await self._repository.soft_delete_all_text(
            conversation_id, actor_id=actor_id, now=datetime.now(UTC)
        )

    async def purge_trip_conversation(self, trip_id: UUID) -> bool:
        """Hard-delete a trip's private chat after the trip ends (community is never touched)."""
        conversation = await self._repository.get_for_trip(trip_id)
        if conversation is None:
            return False
        await self._repository.delete_conversation(conversation.id)
        log.info(
            "trip_conversation_purged",
            trip_id=str(trip_id),
            conversation_id=str(conversation.id),
        )
        return True

    async def admin_delete_conversation(
        self, conversation_id: UUID, *, actor_id: UUID, is_admin: bool
    ) -> None:
        if not is_admin:
            raise ForbiddenError("Only moderators can delete a conversation.")
        conversation = await self._repository.get(conversation_id)
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        if conversation.type is ConversationType.COMMUNITY:
            raise ForbiddenError("Community chat cannot be deleted.")
        await self._repository.delete_conversation(conversation_id)
        log.info(
            "conversation_admin_deleted",
            conversation_id=str(conversation_id),
            actor_id=str(actor_id),
        )

    async def close_completed(self, now: datetime | None = None) -> int:
        moment = now or datetime.now(UTC)
        return await self._repository.close_due(
            moment, self._settings.chat_post_completion_open_hours
        )

    async def _require_member(
        self, conversation_id: UUID, user_id: UUID, *, is_admin: bool
    ) -> Conversation:
        conversation = await self._repository.get(conversation_id)
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        if is_admin:
            return conversation
        if conversation.type is ConversationType.COMMUNITY:
            await self._join_community(user_id)
            return conversation
        member = await self._repository.member(conversation_id, user_id)
        if member is None or member.left_at is not None:
            raise NotFoundError("Conversation not found.")
        return conversation

    async def _join_community(self, user_id: UUID) -> Conversation:
        conversation, created = await self._repository.ensure_community()
        if created:
            await self._system_message(
                conversation.id,
                SystemEvent.CONVERSATION_OPENED,
                body=(
                    "اتفتحت دردشة المجتمع. أي عضو يقدر يكتب هنا. / "
                    "Community chat is open. Any member can write here."
                ),
            )
        member = await self._repository.member(conversation.id, user_id)
        if member is None or member.left_at is not None:
            await self._repository.add_member(conversation.id, user_id, now=datetime.now(UTC))
        return conversation

    async def _system_message(
        self, conversation_id: UUID, event: SystemEvent, *, body: str | None = None
    ) -> None:
        if body is None:
            # Prefer Arabic as the product default; the UI can still localise via systemEvent.
            copy = _SYSTEM_COPY[event]
            body = copy["ar"]
        message = Message(
            id=uuid7(),
            conversation_id=conversation_id,
            sender_id=None,
            kind=MessageKind.SYSTEM,
            body=body,
            system_event=event.value,
        )
        await self._repository.insert_message(message)

    async def _conversation_view(
        self, conversation: Conversation, *, viewer_id: UUID
    ) -> ConversationView:
        last = await self._repository.last_message(conversation.id)
        last_view = (await self._message_views([last]))[0] if last is not None else None
        unread = await self._repository.unread_count(conversation.id, viewer_id)
        members = await self._repository.active_member_ids(conversation.id)
        names = await self._repository.display_names(members)
        membership = await self._repository.member(conversation.id, viewer_id)
        muted = bool(membership is not None and membership.left_at is None and membership.muted)
        origin = destination = None
        departure = None
        if conversation.trip_id is not None:
            summaries = await self._repository.trip_summaries((conversation.trip_id,))
            found = summaries.get(conversation.trip_id)
            if found is not None:
                origin, destination, departure, _driver = found
        return ConversationView(
            id=conversation.id,
            trip_id=conversation.trip_id,
            origin_label=origin,
            destination_label=destination,
            departure_at=departure,
            is_read_only=conversation.is_read_only,
            unread_count=unread,
            muted=muted,
            last_message=last_view,
            member_ids=tuple(members),
            member_names=tuple(names.get(user_id, "") for user_id in members),
        )

    async def set_muted(
        self, conversation_id: UUID, *, viewer_id: UUID, muted: bool
    ) -> ConversationView:
        await self._require_member(conversation_id, viewer_id, is_admin=False)
        updated = await self._repository.set_muted(conversation_id, viewer_id, muted=muted)
        if updated is None:
            raise NotFoundError("Conversation membership not found.")
        conversation = await self._repository.get(conversation_id)
        if conversation is None:
            raise NotFoundError("Conversation not found.")
        return await self._conversation_view(conversation, viewer_id=viewer_id)

    async def _message_views(self, rows: list[Message]) -> list[MessageView]:
        senders = [row.sender_id for row in rows if row.sender_id is not None]
        names = await self._repository.display_names(senders)
        views: list[MessageView] = []
        for row in rows:
            deleted = row.deleted_at is not None
            views.append(
                MessageView(
                    id=row.id,
                    conversation_id=row.conversation_id,
                    sender_id=row.sender_id,
                    sender_display_name=(
                        names.get(row.sender_id) if row.sender_id is not None else None
                    ),
                    kind=row.kind,
                    body="" if deleted else row.body,
                    system_event=row.system_event,
                    created_at=row.created_at,
                    deleted=deleted,
                )
            )
        return views


def _body(value: str, max_length: int) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationAppError("Message cannot be empty.")
    if len(cleaned) > min(max_length, MESSAGE_MAX_LENGTH):
        raise ValidationAppError(f"Message must be {max_length} characters or fewer.")
    return cleaned


def chat_service_for(
    db: AsyncSession,
    settings: Settings,
    *,
    events: EventPublisher | None = None,
    blocks: BlockChecker | None = None,
    limiter: RateLimiter | None = None,
) -> ChatService:
    return ChatService(ChatRepository(db), settings, events=events, blocks=blocks, limiter=limiter)
