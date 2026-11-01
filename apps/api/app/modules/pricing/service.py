"""Integer-only suggested contribution (BR-PRICE-01…06)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from app.core.errors import ServiceUnavailableError
from app.modules.pricing.models import CURRENCY_EGP, PricingRule
from app.modules.pricing.repository import PricingRepository

_ONE = Decimal("1")


@dataclass(frozen=True, slots=True)
class PriceQuote:
    rule_id: UUID
    currency: str
    passenger_price_minor: int
    platform_fee_minor: int
    driver_amount_minor: int
    distance_m: int


def passenger_price_minor(rule: PricingRule, distance_m: int) -> int:
    """``base + round(per_km x km)`` using half-up rounding on whole piastres."""
    kilometres = Decimal(distance_m) / Decimal(1000)
    distance_fee = (Decimal(rule.per_km_minor) * kilometres).quantize(_ONE, rounding=ROUND_HALF_UP)
    return int(rule.base_fee_minor + distance_fee)


class PricingService:
    def __init__(self, repository: PricingRepository) -> None:
        self._repository = repository

    async def quote(self, distance_m: int, *, at: datetime | None = None) -> PriceQuote:
        moment = at or datetime.now(UTC)
        rule = await self._repository.active_at(moment)
        if rule is None:
            raise ServiceUnavailableError("No pricing rule is active.")
        passenger = passenger_price_minor(rule, max(distance_m, 0))
        fee = passenger * rule.platform_fee_bps // 10_000
        return PriceQuote(
            rule_id=rule.id,
            currency=rule.currency or CURRENCY_EGP,
            passenger_price_minor=passenger,
            platform_fee_minor=fee,
            driver_amount_minor=passenger - fee,
            distance_m=max(distance_m, 0),
        )
