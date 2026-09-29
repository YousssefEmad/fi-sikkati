"""Require PostgreSQL extensions.

* ``postgis``     — geography/geometry types for routes and matching (ADR-0012)
* ``citext``      — case-insensitive unique emails (database.md §2.1)
* ``btree_gist``  — exclusion constraints mixing scalar + range columns (pricing_rules)

Installing an extension needs superuser (or a "trusted" extension), which the migrator role
deliberately does not have (database.md §8). The platform/DBA provisions extensions
(locally: ``infra/compose/postgres/init``). This revision therefore *verifies* they exist and
fails with an actionable message otherwise, and creates them only when the connected role is
allowed to (e.g. CI containers running as superuser).

Revision ID: 0001
Revises: None
Create Date: 2026-09-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REQUIRED_EXTENSIONS: tuple[str, ...] = ("postgis", "citext", "btree_gist")


def _installed_extensions() -> set[str]:
    result = op.get_bind().execute(sa.text("SELECT extname FROM pg_extension"))
    return {row[0] for row in result}


def _is_superuser() -> bool:
    return bool(
        op.get_bind()
        .execute(sa.text("SELECT rolsuper FROM pg_roles WHERE rolname = current_user"))
        .scalar()
    )


def upgrade() -> None:
    missing = [name for name in REQUIRED_EXTENSIONS if name not in _installed_extensions()]
    if not missing:
        return
    if _is_superuser():
        for name in missing:
            op.execute(f'CREATE EXTENSION IF NOT EXISTS "{name}"')
        return
    msg = (
        "Required PostgreSQL extensions are not installed: "
        + ", ".join(missing)
        + ". Ask the database administrator to run CREATE EXTENSION for them "
        "(locally: recreate the compose volume so infra/compose/postgres/init runs)."
    )
    raise RuntimeError(msg)


def downgrade() -> None:
    # Extensions are provisioned outside migrations; dropping them would also drop every
    # dependent object in the database. Intentionally a no-op.
    return
