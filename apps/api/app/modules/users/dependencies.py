"""FastAPI wiring for the users module."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.lifecycle import (
    CancellationStats,
    DeletionGuard,
    get_cancellation_stats,
    get_deletion_guard,
)
from app.modules.users.repository import UserRepository
from app.modules.users.service import UserService


def get_user_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    guard: Annotated[DeletionGuard, Depends(get_deletion_guard)],
    cancellations: Annotated[CancellationStats, Depends(get_cancellation_stats)],
) -> UserService:
    return UserService(UserRepository(db), settings, guard, cancellations)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
