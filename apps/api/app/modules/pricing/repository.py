"""Load the pricing rule in force at a given instant."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.pricing.models import PricingRule


class PricingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def active_at(self, moment: datetime) -> PricingRule | None:
        result = await self._db.execute(
            select(PricingRule)
            .where(
                PricingRule.effective_from <= moment,
                (PricingRule.effective_to.is_(None)) | (PricingRule.effective_to > moment),
            )
            .order_by(PricingRule.effective_from.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
