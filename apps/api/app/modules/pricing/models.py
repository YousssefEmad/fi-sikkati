"""``pricing_rules`` (database.md §2.8)."""

from __future__ import annotations

from datetime import datetime
from typing import Final
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, uuid_primary_key

CURRENCY_EGP: Final = "EGP"


class PricingRule(Base, TimestampMixin):
    __tablename__ = "pricing_rules"
    __table_args__ = (
        CheckConstraint("base_fee_minor >= 0", name="base_fee_non_negative"),
        CheckConstraint("per_km_minor >= 0", name="per_km_non_negative"),
        CheckConstraint(
            "platform_fee_bps >= 0 AND platform_fee_bps <= 10000", name="platform_fee_bps_range"
        ),
        CheckConstraint("char_length(currency) = 3", name="currency_iso"),
        Index("ix_pricing_rules_effective_from", "effective_from"),
    )

    id: Mapped[UUID] = uuid_primary_key()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False, default=CURRENCY_EGP)
    base_fee_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    per_km_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    platform_fee_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[UUID | None] = mapped_column(nullable=True)
