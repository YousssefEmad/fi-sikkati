"""``ai_interactions`` (database.md §2.9)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Final
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, CreatedAtMixin, uuid_primary_key


class AiOutcome(StrEnum):
    ANSWERED = "ANSWERED"
    REFUSED = "REFUSED"
    ERROR = "ERROR"


AI_OUTCOME_ENUM: Final = Enum(
    AiOutcome, name="ai_interactions_outcome_enum", values_callable=lambda m: [i.value for i in m]
)


class AiInteraction(Base, CreatedAtMixin):
    __tablename__ = "ai_interactions"
    __table_args__ = (Index("ix_ai_interactions_user_id_created_at", "user_id", "created_at"),)

    id: Mapped[UUID] = uuid_primary_key()
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    prompt_hash: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    outcome: Mapped[AiOutcome] = mapped_column(AI_OUTCOME_ENUM, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
