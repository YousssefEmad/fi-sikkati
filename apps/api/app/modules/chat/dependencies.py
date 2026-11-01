"""Chat FastAPI wiring."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.events import event_publisher_for
from app.core.lifecycle import get_block_checker
from app.core.rate_limit import RateLimiter, get_rate_limiter
from app.modules.chat.repository import ChatRepository
from app.modules.chat.service import ChatService


def get_chat_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> ChatService:
    return ChatService(
        ChatRepository(db),
        settings,
        events=event_publisher_for(request, db),
        blocks=get_block_checker(request),
        limiter=limiter,
    )


ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
