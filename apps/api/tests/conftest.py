"""Shared test fixtures.

Environment variables are set *before* ``app`` modules are imported so ``Settings`` resolves
without a ``.env`` file. Unit and API tests never touch real services; integration tests are
marked ``integration`` and run only when ``RUN_INTEGRATION=1`` (CI provides PostGIS + Redis).
"""

from __future__ import annotations

import base64
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
    # Fixed, obviously-fake secrets: deterministic tokens make failures reproducible, and
    # nothing here is ever used outside the test suite.
    "AUTH_JWT_ACTIVE_KID": "test-1",
    "AUTH_JWT_PRIVATE_KEY": base64.b64encode(b"fi-sikkati-test-ed25519-seed-32b").decode(),
    "AUTH_PASSWORD_PEPPER": "test-pepper-" + "p" * 24,
    "AUTH_CSRF_SECRET": "test-csrf-" + "c" * 24,
    "AUTH_HASH_SECRET": "test-hash-" + "h" * 24,
    # Argon2 at production cost would add minutes to the suite; the parameters themselves are
    # asserted in tests/unit/test_config.py instead.
    "ARGON2_TIME_COST": "1",
    "ARGON2_MEMORY_COST_KIB": "8192",
    "ARGON2_PARALLELISM": "1",
    "EMAIL_FROM_ADDRESS": "no-reply@fisikkati.app",
    "SMTP_HOST": "127.0.0.1",
    "SMTP_PORT": "1025",
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

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.files.memory import MemoryObjectStorage  # noqa: E402
from tests.support.accounts import AccountFactory  # noqa: E402
from tests.support.email import RecordingEmailSender  # noqa: E402
from tests.support.sms import RecordingSmsSender  # noqa: E402

#: Redis logical database used by integration tests, so a developer's local keys survive the
#: ``FLUSHDB`` each test needs to reset rate-limit counters.
TEST_REDIS_DB = 15

#: Everything Phase 2 writes. Truncated between integration tests as the DDL role, because the
#: application role is deliberately not allowed to delete from ``audit_logs``.
_PHASE_3_TABLES = (
    "audit_logs",
    "ai_interactions",
    "moderation_actions",
    "reports",
    "ratings",
    "user_blocks",
    "messages",
    "conversation_members",
    "conversations",
    "notification_preferences",
    "notifications",
    "trip_join_requests",
    "trip_stops",
    "trip_routes",
    "trips",
    "vehicle_documents",
    "driver_verifications",
    "identity_documents",
    "vehicles",
    "password_reset_tokens",
    "phone_verification_codes",
    "email_verification_tokens",
    "auth_sessions",
    "user_roles",
    "user_profiles",
    "stored_files",
    "users",
)


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
        application.state.object_storage = MemoryObjectStorage()
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


# --- Integration fixtures (real PostgreSQL + Redis) -------------------------------------------


@pytest.fixture(scope="session")
def integration_settings(settings: Settings) -> Settings:
    redis_url = str(settings.redis_url).rsplit("/", 1)[0] + f"/{TEST_REDIS_DB}"
    return settings.model_copy(update={"redis_url": redis_url})


@pytest.fixture
async def clean_database(integration_settings: Settings) -> AsyncIterator[None]:
    """Empty the Phase 2 tables before each test using the migration (DDL) role."""
    url = str(integration_settings.migration_database_url or integration_settings.database_url)
    engine = create_async_engine(url)
    statement = text(f"TRUNCATE {', '.join(_PHASE_3_TABLES)} CASCADE")
    try:
        async with engine.begin() as connection:
            await connection.execute(statement)
        yield
    finally:
        await engine.dispose()


@pytest.fixture
async def api_app(integration_settings: Settings, clean_database: None) -> AsyncIterator[FastAPI]:
    """The real application wired to the test database, with email captured in memory."""
    application = create_app(integration_settings)
    async with LifespanManager(application):
        application.state.email_sender = RecordingEmailSender()
        application.state.sms_sender = RecordingSmsSender()
        application.state.object_storage = MemoryObjectStorage()
        # Rate-limit counters must not leak between tests: every test shares one client "IP".
        await application.state.redis.flushdb()
        yield application


@pytest.fixture
def sent_emails(api_app: FastAPI) -> RecordingEmailSender:
    sender = api_app.state.email_sender
    assert isinstance(sender, RecordingEmailSender)
    return sender


@pytest.fixture
async def api_client(api_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """HTTPS base URL so the ``Secure`` session cookies are accepted by the client jar."""
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as http:
        yield http


@pytest.fixture
async def second_client(api_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """A second browser: its own cookie jar, the same application and database."""
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="https://testserver") as http:
        yield http


@pytest.fixture
def sent_sms(api_app: FastAPI) -> RecordingSmsSender:
    sender = api_app.state.sms_sender
    assert isinstance(sender, RecordingSmsSender)
    return sender


@pytest.fixture
def accounts(
    api_client: AsyncClient,
    sent_emails: RecordingEmailSender,
    sent_sms: RecordingSmsSender,
    integration_settings: Settings,
) -> AccountFactory:
    return AccountFactory(api_client, sent_emails, integration_settings, sent_sms)


@pytest.fixture
def second_accounts(
    second_client: AsyncClient,
    sent_emails: RecordingEmailSender,
    sent_sms: RecordingSmsSender,
    integration_settings: Settings,
) -> AccountFactory:
    return AccountFactory(second_client, sent_emails, integration_settings, sent_sms)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("RUN_INTEGRATION") == "1":
        return
    skip = pytest.mark.skip(reason="integration tests run only with RUN_INTEGRATION=1")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)
