"""Bodies for ``POST /ai/assistant``."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiModel


class AssistantRequest(ApiModel):
    message: Annotated[str, Field(min_length=1, max_length=1000)]
    conversation_id: UUID | None = None


class SearchHint(ApiModel):
    origin_query: str | None = None
    destination_query: str | None = None
    date: str | None = None
    time: str | None = None


class AssistantResponse(ApiModel):
    answer: str
    search_params: SearchHint | None = None
    trip_ids: list[UUID]
    interaction_id: UUID
    provider: str
