"""Assistant orchestration: flag, rate limit, provider, audit row."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import FeatureDisabledError
from app.core.ids import uuid7
from app.core.rate_limit import RateLimit, RateLimiter
from app.core.security import keyed_hash
from app.modules.ai.models import AiInteraction, AiOutcome
from app.modules.ai.rules import RuleResult, interpret
from app.modules.ai.schemas import AssistantResponse, SearchHint

EnabledCheck = Callable[[], Awaitable[bool]]


class AiService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings,
        *,
        limiter: RateLimiter,
        enabled: EnabledCheck,
    ) -> None:
        self._db = db
        self._settings = settings
        self._limiter = limiter
        self._enabled = enabled

    async def ask(self, *, user_id: UUID, message: str, hash_secret: str) -> AssistantResponse:
        if not await self._enabled():
            raise FeatureDisabledError("The assistant is not enabled.")
        await self._limiter.enforce(
            RateLimit.parse("ai_assistant", self._settings.ai_rate_limit_per_user),
            keyed_hash(f"ai:{user_id}", hash_secret),
        )
        started = perf_counter()
        result = interpret(message)
        latency = int((perf_counter() - started) * 1000)
        interaction = AiInteraction(
            id=uuid7(),
            user_id=user_id,
            prompt_hash=keyed_hash(message.strip().casefold(), hash_secret),
            tool_calls=[{"tool": "rules.interpret"}],
            outcome=AiOutcome.ANSWERED,
            latency_ms=max(latency, 0),
        )
        self._db.add(interaction)
        await self._db.flush()
        return _response(interaction.id, result, provider="rules")


def _response(interaction_id: UUID, result: RuleResult, *, provider: str) -> AssistantResponse:
    hint = None
    if result.origin or result.destination:
        hint = SearchHint(origin_query=result.origin, destination_query=result.destination)
    return AssistantResponse(
        answer=result.answer,
        search_params=hint,
        trip_ids=[],
        interaction_id=interaction_id,
        provider=provider,
    )
