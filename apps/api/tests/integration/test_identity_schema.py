"""Phase 2 schema: constraints the application must not be able to violate."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import Settings
from app.core.database import Database

pytestmark = pytest.mark.integration

_USER_INSERT = """
INSERT INTO users (
    id, email, password_hash, date_of_birth, terms_version, privacy_version,
    legal_accepted_at, locale
) VALUES (
    :id, :email, 'hash', '1990-01-01', 'v', 'v', NOW(), 'en'
)
"""


async def test_app_role_cannot_update_or_delete_audit_logs(settings: Settings) -> None:
    """database.md §8: history is append-only for the runtime role."""
    database = Database(settings)
    try:
        async with database.engine.connect() as connection:
            with pytest.raises(DBAPIError, match="permission denied"):
                await connection.execute(text("UPDATE audit_logs SET action = 'AUTH_LOGOUT'"))
        async with database.engine.connect() as connection:
            with pytest.raises(DBAPIError, match="permission denied"):
                await connection.execute(text("DELETE FROM audit_logs"))
    finally:
        await database.dispose()


async def test_users_email_is_unique_case_insensitively(
    settings: Settings, clean_database: None
) -> None:
    del clean_database
    database = Database(settings)
    try:
        async with database.engine.connect() as connection:
            await connection.execute(
                text(_USER_INSERT), {"id": uuid4(), "email": "Unique.Check@example.com"}
            )
            await connection.commit()
            with pytest.raises(DBAPIError, match="unique"):
                await connection.execute(
                    text(_USER_INSERT), {"id": uuid4(), "email": "unique.check@example.com"}
                )
    finally:
        await database.dispose()
