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
