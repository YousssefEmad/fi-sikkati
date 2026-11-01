from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_BASE = {
    "APP_ENV": "test",
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db",
    "REDIS_URL": "redis://localhost:6379/0",
    "PUBLIC_WEB_URL": "http://localhost:3000",
    "AUTH_JWT_ACTIVE_KID": "test-1",
    "AUTH_JWT_PRIVATE_KEY": "dGVzdC1qd3Qtc2VlZC0zMmJ5dGVzLWxvbmcgIQ==",
    "AUTH_PASSWORD_PEPPER": "test-pepper-" + "p" * 24,
    "AUTH_CSRF_SECRET": "test-csrf-" + "c" * 24,
    "AUTH_HASH_SECRET": "test-hash-" + "h" * 24,
    "EMAIL_FROM_ADDRESS": "no-reply@fisikkati.app",
    "SMTP_HOST": "127.0.0.1",
}


def test_cors_origins_split_from_comma_separated_string() -> None:
    settings = Settings.model_validate(
        {**_BASE, "CORS_ORIGINS": "http://localhost:3000, https://app.example.com/"}
    )
    assert settings.cors_origin_strings == ["http://localhost:3000", "https://app.example.com"]


def test_sync_driver_is_rejected() -> None:
    with pytest.raises(ValidationError, match="postgresql\\+asyncpg"):
        Settings.model_validate({**_BASE, "DATABASE_URL": "postgresql://u:p@localhost/db"})


def test_missing_required_values_fail_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _BASE:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    ("env", "docs"),
    [("development", True), ("test", True), ("staging", True), ("production", False)],
)
def test_docs_only_outside_production(env: str, docs: bool) -> None:
    production = {
        "VAPID_PUBLIC_KEY": "public",
        "VAPID_PRIVATE_KEY": "private-key",
        "TWILIO_ACCOUNT_SID": "AC123",
        "TWILIO_AUTH_TOKEN": "token",
        "SMS_FROM": "+15005550006",
    }
    settings = Settings.model_validate(
        {**_BASE, "APP_ENV": env, **(production if env == "production" else {})}
    )
    assert settings.docs_enabled is docs


def test_short_secrets_are_rejected() -> None:
    with pytest.raises(ValidationError, match="at least 32"):
        Settings.model_validate({**_BASE, "AUTH_PASSWORD_PEPPER": "too-short"})


def test_absolute_refresh_ttl_cannot_be_shorter_than_sliding() -> None:
    with pytest.raises(ValidationError, match="AUTH_REFRESH_ABSOLUTE_TTL_DAYS"):
        Settings.model_validate(
            {**_BASE, "AUTH_REFRESH_TOKEN_TTL_DAYS": 60, "AUTH_REFRESH_ABSOLUTE_TTL_DAYS": 30}
        )
