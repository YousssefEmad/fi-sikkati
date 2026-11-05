"""SQL for trip conversations."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import uuid7
from app.modules.chat.models import (
    Conversation,
    ConversationMember,
    ConversationType,
    Message,
    MessageKind,
)
from app.modules.trips.models import Trip
from app.modules.users.models import UserProfile


class ChatRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    @property
    def session(self) -> AsyncSession:
        return self._db

    async def get(self, conversation_id: UUID) -> Conversation | None:
        return await self._db.get(Conversation, conversation_id)

    async def get_for_trip(self, trip_id: UUID) -> Conversation | None:
        result = await self._db.execute(select(Conversation).where(Conversation.trip_id == trip_id))
        return result.scalar_one_or_none()

    async def ensure_community(self) -> tuple[Conversation, bool]:
        """Return the single community room, creating it once."""
        await self._db.execute(text("SELECT pg_advisory_xact_lock(814201)"))
        existing = await self._db.execute(
            select(Conversation).where(Conversation.type == ConversationType.COMMUNITY).limit(1)
        )
        found = existing.scalar_one_or_none()
        if found is not None:
            return found, False
        conversation = Conversation(
            id=uuid7(), type=ConversationType.COMMUNITY, trip_id=None, is_read_only=False
        )
        self._db.add(conversation)
        await self._db.flush()
        return conversation, True

    async def get_trip(self, trip_id: UUID) -> Trip | None:
        return await self._db.get(Trip, trip_id)

    async def create_trip_conversation(self, trip_id: UUID) -> Conversation:
        conversation = Conversation(
            id=uuid7(), type=ConversationType.TRIP, trip_id=trip_id, is_read_only=False
        )
        self._db.add(conversation)
        await self._db.flush()
        return conversation

    async def member(self, conversation_id: UUID, user_id: UUID) -> ConversationMember | None:
        return await self._db.get(ConversationMember, (conversation_id, user_id))

    async def add_member(self, conversation_id: UUID, user_id: UUID, *, now: datetime) -> None:
        statement = (
            insert(ConversationMember)
            .values(
                conversation_id=conversation_id,
                user_id=user_id,
                joined_at=now,
                left_at=None,
                muted=False,
            )
            .on_conflict_do_update(
                index_elements=["conversation_id", "user_id"],
                set_={"left_at": None, "joined_at": now, "updated_at": now},
            )
        )
        await self._db.execute(statement)

    async def leave(self, conversation_id: UUID, user_id: UUID, *, now: datetime) -> None:
        await self._db.execute(
            update(ConversationMember)
            .where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.user_id == user_id,
                ConversationMember.left_at.is_(None),
            )
            .values(left_at=now)
        )

    async def active_member_ids(self, conversation_id: UUID) -> list[UUID]:
        result = await self._db.execute(
            select(ConversationMember.user_id).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.left_at.is_(None),
            )
        )
        return list(result.scalars())

    async def active_notify_member_ids(self, conversation_id: UUID) -> list[UUID]:
        """Active members who have not muted this conversation (for alerts/push)."""
        result = await self._db.execute(
            select(ConversationMember.user_id).where(
                ConversationMember.conversation_id == conversation_id,
                ConversationMember.left_at.is_(None),
                ConversationMember.muted.is_(False),
            )
        )
        return list(result.scalars())

    async def set_muted(
        self, conversation_id: UUID, user_id: UUID, *, muted: bool
    ) -> ConversationMember | None:
        member = await self.member(conversation_id, user_id)
        if member is None or member.left_at is not None:
            return None
        member.muted = muted
        await self._db.flush()
        return member

    async def set_read_only(self, conversation: Conversation, value: bool) -> None:
        conversation.is_read_only = value

    async def delete_conversation(self, conversation_id: UUID) -> None:
        """Hard-delete a conversation; members and messages cascade from the DB."""
        conversation = await self.get(conversation_id)
        if conversation is None:
            return
        await self._db.delete(conversation)
        await self._db.flush()

    async def list_for_user(
        self, user_id: UUID, *, before: tuple[datetime, UUID] | None, limit: int
    ) -> list[Conversation]:
        latest = (
            select(
                Message.conversation_id,
                func.max(Message.created_at).label("last_at"),
            )
            .group_by(Message.conversation_id)
            .subquery()
        )
        query = (
            select(Conversation)
            .join(
                ConversationMember,
                ConversationMember.conversation_id == Conversation.id,
            )
            .outerjoin(latest, latest.c.conversation_id == Conversation.id)
            .where(
                ConversationMember.user_id == user_id,
                ConversationMember.left_at.is_(None),
            )
        )
        if before is not None:
            stamp, ident = before
            last_at = func.coalesce(latest.c.last_at, Conversation.created_at)
            query = query.where(
                (last_at < stamp) | ((last_at == stamp) & (Conversation.id < ident))
            )
        query = query.order_by(
            func.coalesce(latest.c.last_at, Conversation.created_at).desc(),
            Conversation.id.desc(),
        ).limit(limit)
        result = await self._db.execute(query)
        return list(result.scalars().unique())

    async def last_message(self, conversation_id: UUID) -> Message | None:
        result = await self._db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def unread_count(self, conversation_id: UUID, user_id: UUID) -> int:
        member = await self.member(conversation_id, user_id)
        if member is None:
            return 0
        query = (
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
            )
        )
        if member.last_read_message_id is not None:
            query = query.where(Message.id > member.last_read_message_id)
        value = await self._db.scalar(query)
        return int(value or 0)

    async def list_messages(
        self,
        conversation_id: UUID,
        *,
        before_id: UUID | None,
        limit: int,
        include_deleted: bool,
    ) -> list[Message]:
        query = select(Message).where(Message.conversation_id == conversation_id)
        if not include_deleted:
            query = query.where(Message.deleted_at.is_(None))
        if before_id is not None:
            query = query.where(Message.id < before_id)
        query = query.order_by(Message.id.desc()).limit(limit)
        result = await self._db.execute(query)
        return list(result.scalars())

    async def get_message(self, message_id: UUID) -> Message | None:
        return await self._db.get(Message, message_id)

    async def get_by_client_id(self, sender_id: UUID, client_message_id: UUID) -> Message | None:
        result = await self._db.execute(
            select(Message).where(
                Message.sender_id == sender_id,
                Message.client_message_id == client_message_id,
            )
        )
        return result.scalar_one_or_none()

    async def insert_message(self, message: Message) -> None:
        async with self._db.begin_nested():
            self._db.add(message)
            await self._db.flush()

    async def mark_read(self, conversation_id: UUID, user_id: UUID, message_id: UUID) -> None:
        member = await self.member(conversation_id, user_id)
        if member is None:
            return
        current = member.last_read_message_id
        if current is None or message_id > current:
            member.last_read_message_id = message_id

    async def soft_delete(self, message: Message, *, actor_id: UUID, now: datetime) -> None:
        message.deleted_at = now
        message.deleted_by = actor_id

    async def soft_delete_ids(
        self,
        conversation_id: UUID,
        message_ids: Sequence[UUID],
        *,
        actor_id: UUID,
        now: datetime,
    ) -> int:
        if not message_ids:
            return 0
        result = await self._db.execute(
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.id.in_(tuple(message_ids)),
                Message.deleted_at.is_(None),
                Message.kind == MessageKind.TEXT,
            )
            .values(deleted_at=now, deleted_by=actor_id)
        )
        return int(result.rowcount or 0) if isinstance(result, CursorResult) else 0

    async def soft_delete_all_text(
        self, conversation_id: UUID, *, actor_id: UUID, now: datetime
    ) -> int:
        result = await self._db.execute(
            update(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.deleted_at.is_(None),
                Message.kind == MessageKind.TEXT,
            )
            .values(deleted_at=now, deleted_by=actor_id)
        )
        return int(result.rowcount or 0) if isinstance(result, CursorResult) else 0

    async def display_names(self, user_ids: Sequence[UUID]) -> dict[UUID, str]:
        if not user_ids:
            return {}
        result = await self._db.execute(
            select(UserProfile.user_id, UserProfile.display_name).where(
                UserProfile.user_id.in_(tuple(user_ids))
            )
        )
        return {row[0]: str(row[1]) for row in result}

    async def trip_summaries(
        self, trip_ids: Sequence[UUID]
    ) -> dict[UUID, tuple[str, str, datetime, UUID]]:
        """``trip_id → (origin, destination, departure_at, driver_id)``."""
        if not trip_ids:
            return {}
        result = await self._db.execute(
            select(
                Trip.id,
                Trip.origin_label,
                Trip.destination_label,
                Trip.departure_at,
                Trip.driver_id,
            ).where(Trip.id.in_(tuple(trip_ids)))
        )
        return {row[0]: (str(row[1]), str(row[2]), row[3], row[4]) for row in result}

    async def close_due(self, now: datetime, hours: int) -> int:
        """BR-CHAT-04: lock conversations whose trip completed more than ``hours`` ago."""
        cutoff = now - timedelta(hours=hours)
        result = await self._db.execute(
            update(Conversation)
            .where(
                Conversation.is_read_only.is_(False),
                Conversation.trip_id.in_(
                    select(Trip.id).where(
                        Trip.completed_at.is_not(None),
                        Trip.completed_at <= cutoff,
                    )
                ),
            )
            .values(is_read_only=True)
        )
        return int(result.rowcount or 0) if isinstance(result, CursorResult) else 0
