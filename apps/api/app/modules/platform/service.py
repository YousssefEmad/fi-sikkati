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
    )
