from __future__ import annotations

from app.core.config import Settings
from app.modules.platform.schemas import PublicConfig

SUPPORTED_LOCALES: tuple[str, ...] = ("ar", "en")
DEFAULT_LOCALE = "ar"
DEFAULT_TIMEZONE = "Africa/Cairo"


def build_public_config(settings: Settings) -> PublicConfig:
    return PublicConfig(
        environment=settings.app_env,
        api_version=settings.api_version,
        supported_locales=list(SUPPORTED_LOCALES),
        default_locale=DEFAULT_LOCALE,
        default_timezone=DEFAULT_TIMEZONE,
        password_min_length=settings.auth_password_min_length,
        minimum_age_years=settings.accounts_minimum_age_years,
        terms_version=settings.legal_terms_version,
        privacy_version=settings.legal_privacy_version,
        deletion_grace_days=settings.accounts_deletion_grace_days,
        max_document_bytes=settings.uploads_max_document_bytes,
        max_vehicles_per_driver=settings.vehicles_max_per_driver,
        review_sla_hours=settings.verification_review_sla_hours,
        identity_document_types=["NATIONAL_ID_FRONT", "NATIONAL_ID_BACK", "SELFIE"],
        vehicle_document_types=["REGISTRATION_FRONT", "REGISTRATION_BACK", "VEHICLE_PHOTO"],
        max_passenger_seats=settings.trips_max_passenger_seats,
        suggested_price_label="suggested_contribution",
        mapbox_public_token=settings.mapbox_public_token,
        vapid_public_key=settings.vapid_public_key or None,
        matching_corridor_width_meters=settings.matching_corridor_width_meters,
        matching_stop_proximity_meters=settings.matching_stop_proximity_meters,
        matching_default_time_window_minutes=settings.matching_default_time_window_minutes,
        email_delivery_enabled=settings.smtp_configured,
        email_verification_required=settings.is_production or settings.smtp_configured,
    )
