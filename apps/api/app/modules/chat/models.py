"""``conversations``, ``conversation_members`` and ``messages`` (database.md §2.5)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Final
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, TimestampMixin, uuid_primary_key

MESSAGE_MAX_LENGTH = 2000


class ConversationType(StrEnum):
    TRIP = "TRIP"
    COMMUNITY = "COMMUNITY"


class MessageKind(StrEnum):
    TEXT = "TEXT"
    SYSTEM = "SYSTEM"


class SystemEvent(StrEnum):
    CONVERSATION_OPENED = "CONVERSATION_OPENED"
    PASSENGER_JOINED = "PASSENGER_JOINED"
    PASSENGER_LEFT = "PASSENGER_LEFT"
    TRIP_UPDATED = "TRIP_UPDATED"
    TRIP_STARTED = "TRIP_STARTED"
    TRIP_CANCELLED = "TRIP_CANCELLED"
    TRIP_COMPLETED = "TRIP_COMPLETED"
    CONVERSATION_CLOSED = "CONVERSATION_CLOSED"


def _pg_enum(enum: type[StrEnum], name: str) -> Enum:
    return Enum(enum, name=name, values_callable=lambda members: [m.value for m in members])


CONVERSATION_TYPE_ENUM: Final = _pg_enum(ConversationType, "conversations_type_enum")
MESSAGE_KIND_ENUM: Final = _pg_enum(MessageKind, "messages_kind_enum")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("trip_id", name="uq_conversations_trip_id"),
        CheckConstraint(
            "(type = 'TRIP' AND trip_id IS NOT NULL) OR (type <> 'TRIP' AND trip_id IS NULL)",
            name="trip_type_has_trip",
        ),
    )

    id: Mapped[UUID] = uuid_primary_key()
    type: Mapped[ConversationType] = mapped_column(
        CONVERSATION_TYPE_ENUM,
        nullable=False,
        default=ConversationType.TRIP,
        server_default=ConversationType.TRIP.value,
    )
    trip_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), nullable=True
    )
    is_read_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ConversationMember(Base, TimestampMixin):
    __tablename__ = "conversation_members"
    __table_args__ = (
        Index(
            "ix_conversation_members_user_active",
            "user_id",
            postgresql_where=text("left_at IS NULL"),
        ),
    )

    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_read_message_id: Mapped[UUID | None] = mapped_column(nullable=True)
    muted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Message(Base, CreatedAtMixin):
    """Append-only. Soft-deleted by moderation; never hard-deleted (database.md §2.5)."""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "char_length(body) BETWEEN 1 AND 2000",
            name="body_length",
        ),
        CheckConstraint(
            "(kind = 'SYSTEM' AND sender_id IS NULL AND system_event IS NOT NULL) OR "
            "(kind = 'TEXT' AND sender_id IS NOT NULL AND system_event IS NULL)",
            name="kind_fields",
        ),
        Index("ix_messages_conversation_id", "conversation_id", "id"),
        Index(
            "uq_messages_sender_client_message",
            "sender_id",
            "client_message_id",
            unique=True,
            postgresql_where=text("client_message_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = uuid_primary_key()
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[MessageKind] = mapped_column(MESSAGE_KIND_ENUM, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    system_event: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_message_id: Mapped[UUID | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
