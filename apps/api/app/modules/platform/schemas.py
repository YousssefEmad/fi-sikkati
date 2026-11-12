from __future__ import annotations

from typing import Literal

from app.core.schemas import ApiModel


class PublicConfig(ApiModel):
    """Non-sensitive runtime configuration the web client needs before login."""

    environment: Literal["development", "test", "staging", "production"]
    api_version: str
    supported_locales: list[str]
    default_locale: str
    default_timezone: str
    password_min_length: int
    minimum_age_years: int
    terms_version: str
    privacy_version: str
    deletion_grace_days: int
    max_document_bytes: int
    max_vehicles_per_driver: int
    review_sla_hours: int
    identity_document_types: list[str]
    vehicle_document_types: list[str]
    max_passenger_seats: int
    suggested_price_label: str
    mapbox_public_token: str | None
    vapid_public_key: str | None
    matching_corridor_width_meters: int
    matching_stop_proximity_meters: int
    matching_default_time_window_minutes: int
    # False when outbound SMTP is unavailable (staging/dev without a real mailbox).
    email_delivery_enabled: bool
    # False when new accounts are auto-verified because email delivery is off.
    email_verification_required: bool
