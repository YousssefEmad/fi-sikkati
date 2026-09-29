"""Real-service checks (PostGIS + Redis). Run with ``RUN_INTEGRATION=1`` after migrations."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.core.config import Settings
from app.core.database import Database
from app.core.redis import create_redis, ping_redis

pytestmark = pytest.mark.integration


async def test_database_reachable_and_extensions_installed(settings: Settings) -> None:
    database = Database(settings)
    try:
        await database.ping()
        async with database.engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT extname FROM pg_extension "
                    "WHERE extname IN ('postgis', 'citext', 'btree_gist')"
                )
            )
            installed = {row[0] for row in result}
    finally:
        await database.dispose()
    assert installed == {"postgis", "citext", "btree_gist"}


async def test_app_role_cannot_run_ddl(settings: Settings) -> None:
    """The runtime role must be DML-only (database.md §8)."""
    database = Database(settings)
    try:
        async with database.engine.connect() as connection:
            with pytest.raises(Exception, match="permission denied"):
                await connection.execute(text("CREATE TABLE _should_fail (id int)"))
    finally:
        await database.dispose()


async def test_redis_reachable(settings: Settings) -> None:
    client = create_redis(settings)
    try:
        await ping_redis(client)
    finally:
        await client.aclose()
