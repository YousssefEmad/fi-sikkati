"""Bodies for ``/conversations`` (api.md §4.8)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiModel
from app.modules.chat.models import MessageKind


class MessageResponse(ApiModel):
    id: UUID
    conversation_id: UUID
    sender_id: UUID | None
    sender_display_name: str | None
    kind: MessageKind
    body: str
    system_event: str | None
    created_at: datetime
    deleted: bool


class ConversationResponse(ApiModel):
    id: UUID
    trip_id: UUID | None
    origin_label: str | None
    destination_label: str | None
    departure_at: datetime | None
    is_read_only: bool
    unread_count: int
    muted: bool = False
    last_message: MessageResponse | None
    member_ids: list[UUID]
    member_names: list[str]


class MuteConversationRequest(ApiModel):
    muted: bool


class ConversationListResponse(ApiModel):
    items: list[ConversationResponse]
    next_cursor: str | None


class MessageListResponse(ApiModel):
    items: list[MessageResponse]
    next_cursor: str | None


class MessageCreate(ApiModel):
    body: Annotated[str, Field(min_length=1, max_length=2000)]
    client_message_id: UUID


class MarkReadRequest(ApiModel):
    message_id: UUID | None = None


class MessageBulkDeleteRequest(ApiModel):
    message_ids: Annotated[list[UUID], Field(min_length=1, max_length=100)]


class ClearConversationResponse(ApiModel):
    deleted_count: int


class MessageBulkDeleteResponse(ApiModel):
    deleted_count: int
