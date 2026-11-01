"""Safety FastAPI wiring and the block-checker port."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.events import event_publisher_for
from app.core.lifecycle import booking_bridge_for
from app.core.rate_limit import RateLimiter, get_rate_limiter
from app.modules.safety.repository import SafetyRepository
from app.modules.safety.service import SafetyBlockChecker, SafetyService


def get_safety_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> SafetyService:
    return SafetyService(
        SafetyRepository(db),
        settings,
        events=event_publisher_for(request, db),
        bridge=booking_bridge_for(request, db),
        limiter=limiter,
    )


SafetyServiceDep = Annotated[SafetyService, Depends(get_safety_service)]


def safety_block_checker() -> SafetyBlockChecker:
    return SafetyBlockChecker()
