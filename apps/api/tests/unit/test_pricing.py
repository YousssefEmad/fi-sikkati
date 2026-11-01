from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.modules.pricing.models import PricingRule
from app.modules.pricing.service import passenger_price_minor


def _rule(base: int, per_km: int) -> PricingRule:
    return PricingRule(
        id=UUID("01924000-aaaa-7000-8000-000000000001"),
        name="test",
        currency="EGP",
        base_fee_minor=base,
        per_km_minor=per_km,
        platform_fee_bps=0,
        effective_from=datetime(2020, 1, 1, tzinfo=UTC),
    )


def test_ten_km_matches_mep_concept() -> None:
    # 10 EGP + 3 EGP/km x 10 km = 40 EGP = 4000 piastres.
    assert passenger_price_minor(_rule(1000, 300), 10_000) == 4000


def test_half_up_rounding_on_partial_kilometre() -> None:
    # 300 x 0.5 = 150 -> 1000 + 150 = 1150.
    assert passenger_price_minor(_rule(1000, 300), 500) == 1150
