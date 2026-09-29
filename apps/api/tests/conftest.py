"""Shared test fixtures.

Environment variables are set *before* ``app`` modules are imported so ``Settings`` resolves
without a ``.env`` file. Unit and API tests never touch real services; integration tests are
marked ``integration`` and run only when ``RUN_INTEGRATION=1`` (CI provides PostGIS + Redis).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

_TEST_ENV = {
    "APP_ENV": "test",
    "LOG_FORMAT": "json",
    "LOG_LEVEL": "WARNING",
    "CORS_ORIGINS": "http://localhost:3000",
    "PUBLIC_WEB_URL": "http://localhost:3000",
}
# Service URLs: explicit env vars win; otherwise a developer's ``apps/api/.env`` (which may
# override host ports) is used by ``Settings``; otherwise the compose defaults below apply.
_SERVICE_DEFAULTS = {
    "DATABASE_URL": "postgresql+asyncpg://fisikkati_app:fisikkati_app_dev@127.0.0.1:5432/fisikkati",
    "MIGRATION_DATABASE_URL": (
        "postgresql+asyncpg://fisikkati_migrator:fisikkati_migrator_dev@127.0.0.1:5432/fisikkati"
    ),
    "REDIS_URL": "redis://127.0.0.1:6379/0",
}
for _key, _value in _TEST_ENV.items():
    os.environ.setdefault(_key, _value)
if not Path(__file__).resolve().parents[1].joinpath(".env").exists():
    for _key, _value in _SERVICE_DEFAULTS.items():
        os.environ.setdefault(_key, _value)

from app.core.config import Settings, get_settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session")
def settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings)
    async with LifespanManager(application):
        # Never hit real services from API tests; integration tests replace these explicitly.
        application.state.health_checks = {}
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("RUN_INTEGRATION") == "1":
        return
    skip = pytest.mark.skip(reason="integration tests run only with RUN_INTEGRATION=1")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
