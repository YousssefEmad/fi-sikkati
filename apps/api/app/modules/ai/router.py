"""``POST /ai/assistant`` (api.md §4.12)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission
from app.core.authz.principal import Principal
from app.core.config import Settings, get_settings
from app.modules.ai.dependencies import AiServiceDep
from app.modules.ai.schemas import AssistantRequest, AssistantResponse

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/assistant",
    response_model=AssistantResponse,
    operation_id="ai_assistant",
    summary="Ask the help and trip-discovery assistant",
)
async def assistant(
    payload: AssistantRequest,
    service: AiServiceDep,
    settings: Annotated[Settings, Depends(get_settings)],
    principal: Annotated[Principal, Depends(require_permission(Permission.AI_ASSISTANT_QUERY))],
) -> AssistantResponse:
    return await service.ask(
        user_id=principal.user_id,
        message=payload.message,
        hash_secret=settings.auth_hash_secret.get_secret_value(),
    )
