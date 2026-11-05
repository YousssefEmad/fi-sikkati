"""``/me/conversations`` and ``/conversations`` (api.md §4.8)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission
from app.core.authz.principal import Principal
from app.core.config import Settings, get_settings
from app.core.pagination import decode_cursor, encode_cursor
from app.modules.chat.dependencies import ChatServiceDep
from app.modules.chat.schemas import (
    ClearConversationResponse,
    ConversationListResponse,
    ConversationResponse,
    MarkReadRequest,
    MessageBulkDeleteRequest,
    MessageBulkDeleteResponse,
    MessageCreate,
    MessageListResponse,
    MessageResponse,
)
from app.modules.chat.service import ConversationView, MessageView

me_router = APIRouter(prefix="/me/conversations", tags=["chat"])
router = APIRouter(prefix="/conversations", tags=["chat"])


def _message(view: MessageView) -> MessageResponse:
    return MessageResponse(
        id=view.id,
        conversation_id=view.conversation_id,
        sender_id=view.sender_id,
        sender_display_name=view.sender_display_name,
        kind=view.kind,
        body=view.body,
        system_event=view.system_event,
        created_at=view.created_at,
        deleted=view.deleted,
    )


def _conversation(view: ConversationView) -> ConversationResponse:
    return ConversationResponse(
        id=view.id,
        trip_id=view.trip_id,
        origin_label=view.origin_label,
        destination_label=view.destination_label,
        departure_at=view.departure_at,
        is_read_only=view.is_read_only,
        unread_count=view.unread_count,
        last_message=None if view.last_message is None else _message(view.last_message),
        member_ids=list(view.member_ids),
        member_names=list(view.member_names),
    )


@me_router.get(
    "",
    response_model=ConversationListResponse,
    operation_id="chat_list_mine",
    summary="Conversations the signed-in user is in",
)
async def list_mine(
    service: ChatServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.CHAT_READ))],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ConversationListResponse:
    rows = await service.list_mine(principal.user_id, before=decode_cursor(cursor), limit=limit + 1)
    page = rows[:limit]
    next_cursor = None
    if len(rows) > limit and page:
        stamp = page[-1].last_message.created_at if page[-1].last_message else page[-1].departure_at
        if stamp is not None:
            next_cursor = encode_cursor(stamp, page[-1].id)
    return ConversationListResponse(
        items=[_conversation(row) for row in page], next_cursor=next_cursor
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
    operation_id="chat_get",
    summary="Read one conversation",
)
async def get_conversation(
    conversation_id: UUID,
    service: ChatServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.CHAT_READ))],
) -> ConversationResponse:
    return _conversation(
        await service.get(conversation_id, viewer_id=principal.user_id, is_admin=principal.is_admin)
    )


@router.get(
    "/{conversation_id}/messages",
    response_model=MessageListResponse,
    operation_id="chat_list_messages",
    summary="Messages in a conversation, newest first",
)
async def list_messages(
    conversation_id: UUID,
    service: ChatServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.CHAT_READ))],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 30,
) -> MessageListResponse:
    before_id = None
    if cursor:
        decoded = decode_cursor(cursor)
        if decoded is not None:
            before_id = decoded[1]
    rows = await service.list_messages(
        conversation_id,
        viewer_id=principal.user_id,
        is_admin=principal.is_admin,
        before_id=before_id,
        limit=limit + 1,
    )
    page = rows[:limit]
    next_cursor = None
    if len(rows) > limit and page:
        next_cursor = encode_cursor(page[-1].created_at, page[-1].id)
    return MessageListResponse(items=[_message(row) for row in page], next_cursor=next_cursor)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    operation_id="chat_send",
    summary="Send a message",
)
async def send_message(
    conversation_id: UUID,
    payload: MessageCreate,
    service: ChatServiceDep,
    settings: Annotated[Settings, Depends(get_settings)],
    principal: Annotated[Principal, Depends(require_permission(Permission.CHAT_SEND))],
) -> MessageResponse:
    view = await service.post(
        conversation_id,
        sender_id=principal.user_id,
        body=payload.body,
        client_message_id=payload.client_message_id,
        hash_secret=settings.auth_hash_secret.get_secret_value(),
    )
    return _message(view)


@router.post(
    "/{conversation_id}/read",
    status_code=204,
    operation_id="chat_mark_read",
    summary="Mark the conversation as read",
)
async def mark_read(
    conversation_id: UUID,
    payload: MarkReadRequest,
    service: ChatServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.CHAT_READ))],
) -> None:
    await service.mark_read(
        conversation_id, viewer_id=principal.user_id, message_id=payload.message_id
    )


@router.delete(
    "/{conversation_id}/messages/{message_id}",
    response_model=MessageResponse,
    operation_id="chat_delete_message",
    summary="Soft-delete one message (author or moderator)",
)
async def delete_message(
    conversation_id: UUID,
    message_id: UUID,
    service: ChatServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.CHAT_SEND))],
) -> MessageResponse:
    return _message(
        await service.remove_message(
            message_id,
            actor_id=principal.user_id,
            is_admin=principal.is_admin,
            conversation_id=conversation_id,
        )
    )


@router.post(
    "/{conversation_id}/messages/delete",
    response_model=MessageBulkDeleteResponse,
    operation_id="chat_delete_messages",
    summary="Soft-delete selected messages (moderators)",
)
async def delete_messages(
    conversation_id: UUID,
    payload: MessageBulkDeleteRequest,
    service: ChatServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.MODERATION_ACTION))],
) -> MessageBulkDeleteResponse:
    count = await service.remove_messages(
        conversation_id,
        list(payload.message_ids),
        actor_id=principal.user_id,
        is_admin=principal.is_admin,
    )
    return MessageBulkDeleteResponse(deleted_count=count)


@router.post(
    "/{conversation_id}/clear",
    response_model=ClearConversationResponse,
    operation_id="chat_clear",
    summary="Clear all user messages in a conversation (moderators)",
)
async def clear_conversation(
    conversation_id: UUID,
    service: ChatServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.MODERATION_ACTION))],
) -> ClearConversationResponse:
    count = await service.clear_conversation(
        conversation_id, actor_id=principal.user_id, is_admin=principal.is_admin
    )
    return ClearConversationResponse(deleted_count=count)


@router.delete(
    "/{conversation_id}",
    status_code=204,
    operation_id="chat_admin_delete",
    summary="Hard-delete a trip conversation (moderators; community protected)",
)
async def admin_delete_conversation(
    conversation_id: UUID,
    service: ChatServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.MODERATION_ACTION))],
) -> None:
    await service.admin_delete_conversation(
        conversation_id, actor_id=principal.user_id, is_admin=principal.is_admin
    )
