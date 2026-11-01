from __future__ import annotations

from app.core.schemas import ApiModel

SUGGESTED_LABEL = "suggested_contribution"


class PriceEstimateResponse(ApiModel):
    distance_m: int
    suggested_price_minor: int
    currency: str
    label: str
