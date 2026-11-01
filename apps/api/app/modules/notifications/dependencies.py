"""Notifications FastAPI wiring."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.service import NotificationService


def get_notification_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> NotificationService:
    return NotificationService(NotificationRepository(db), settings)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
