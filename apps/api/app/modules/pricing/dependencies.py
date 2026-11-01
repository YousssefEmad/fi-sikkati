"""Pricing FastAPI wiring."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.pricing.repository import PricingRepository
from app.modules.pricing.service import PricingService


def get_pricing_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> PricingService:
    return PricingService(PricingRepository(db))


PricingServiceDep = Annotated[PricingService, Depends(get_pricing_service)]
