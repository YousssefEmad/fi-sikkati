"""Unique public display names.

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.modules.users.names import display_name_key

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("display_name_key", sa.Text(), nullable=True))
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT user_id, display_name FROM user_profiles")).fetchall()
    used: set[str] = set()
    for user_id, name in rows:
        base = display_name_key(name) or "member"
        candidate = base
        suffix = 2
        while candidate in used:
            candidate = f"{base}-{suffix}"
            suffix += 1
        used.add(candidate)
        bind.execute(
            sa.text("UPDATE user_profiles SET display_name_key = :key WHERE user_id = :user_id"),
            {"key": candidate, "user_id": user_id},
        )
    op.alter_column("user_profiles", "display_name_key", nullable=False)
    op.create_index(
        "user_profiles_display_name_key_key",
        "user_profiles",
        ["display_name_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("user_profiles_display_name_key_key", table_name="user_profiles")
    op.drop_column("user_profiles", "display_name_key")
