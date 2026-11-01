"""``GET /pricing/estimate`` — display-only suggested contribution (OD-007)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.authz.dependencies import require_permission
from app.core.authz.permissions import Permission
from app.core.authz.principal import Principal
from app.modules.pricing.dependencies import PricingServiceDep
from app.modules.pricing.schemas import SUGGESTED_LABEL, PriceEstimateResponse

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get(
    "/estimate",
    response_model=PriceEstimateResponse,
    operation_id="pricing_estimate",
    summary="Suggested per-seat contribution for a distance",
)
async def estimate(
    service: PricingServiceDep,
    principal: Annotated[Principal, Depends(require_permission(Permission.PRICING_ESTIMATE))],
    distance_m: Annotated[int, Query(ge=0, le=2_000_000, alias="distanceM")],
) -> PriceEstimateResponse:
    del principal
    quote = await service.quote(distance_m)
    return PriceEstimateResponse(
        distance_m=quote.distance_m,
        suggested_price_minor=quote.passenger_price_minor,
        currency=quote.currency,
        label=SUGGESTED_LABEL,
    )
