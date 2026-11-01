"""AI FastAPI wiring."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.rate_limit import RateLimiter, get_rate_limiter
from app.modules.admin.models import AI_FLAG_KEY
from app.modules.admin.repository import AdminRepository
from app.modules.ai.service import AiService


def get_ai_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> AiService:
    repository = AdminRepository(db)

    async def enabled() -> bool:
        if settings.ai_enabled:
            return True
        flag = await repository.get_flag(AI_FLAG_KEY)
        return bool(flag is not None and flag.enabled)

    return AiService(db, settings, limiter=limiter, enabled=enabled)


AiServiceDep = Annotated[AiService, Depends(get_ai_service)]
