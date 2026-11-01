"""Alembic environment (async engine).

The URL comes from ``MIGRATION_DATABASE_URL`` (DDL role) or ``DATABASE_URL`` as a fallback for
local development. PostGIS-managed tables are excluded from autogenerate.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.core.database import Base

# Importing every module's models registers their tables on ``Base.metadata``, which is what
# autogenerate and ``alembic check`` compare the database against.
from app.modules.admin import models as admin_models  # noqa: F401
from app.modules.ai import models as ai_models  # noqa: F401
from app.modules.audit import models as audit_models  # noqa: F401
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.bookings import models as bookings_models  # noqa: F401
from app.modules.chat import models as chat_models  # noqa: F401
from app.modules.files import models as files_models  # noqa: F401
from app.modules.maps import fake as maps_fake  # noqa: F401
from app.modules.notifications import models as notifications_models  # noqa: F401
from app.modules.pricing import models as pricing_models  # noqa: F401
from app.modules.safety import models as safety_models  # noqa: F401
from app.modules.trips import models as trips_models  # noqa: F401
from app.modules.users import models as users_models  # noqa: F401
from app.modules.vehicles import models as vehicles_models  # noqa: F401
from app.modules.verification import models as verification_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Tables owned by PostGIS / extensions that must never appear in autogenerate diffs.
_EXTENSION_TABLES = {"spatial_ref_sys"}


def _database_url() -> str:
    settings = get_settings()
    return str(settings.migration_database_url or settings.database_url)


def include_object(
    obj: object, name: str | None, type_: str, reflected: bool, compare_to: object
) -> bool:
    return not (type_ == "table" and name in _EXTENSION_TABLES)


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _database_url()
    connectable = async_engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
