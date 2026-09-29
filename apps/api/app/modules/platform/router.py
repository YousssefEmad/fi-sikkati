from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.modules.platform.schemas import PublicConfig
from app.modules.platform.service import build_public_config

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get(
    "/config",
    response_model=PublicConfig,
    operation_id="platform_get_public_config",
    summary="Public runtime configuration",
)
async def get_public_config(settings: Annotated[Settings, Depends(get_settings)]) -> PublicConfig:
    return build_public_config(settings)
