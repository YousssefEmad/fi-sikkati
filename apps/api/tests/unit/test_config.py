from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_BASE = {
    "APP_ENV": "test",
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db",
    "REDIS_URL": "redis://localhost:6379/0",
    "PUBLIC_WEB_URL": "http://localhost:3000",
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
    settings = Settings.model_validate({**_BASE, "APP_ENV": env})
    assert settings.docs_enabled is docs
