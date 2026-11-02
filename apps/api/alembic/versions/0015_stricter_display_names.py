"""Recompute display_name_key after digits and near-duplicate folding.

Revision ID: 0015_stricter_display_names
Revises: 0014_phone_verification
Create Date: 2026-11-02
"""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.modules.users.names import display_name_key

revision: str = "0015_stricter_display_names"
down_revision: Union[str, None] = "0014_phone_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT user_id, display_name FROM user_profiles")).fetchall()
    claimed: dict[str, int] = defaultdict(int)
    for user_id, name in rows:
        base = display_name_key(name) or "member"
        claimed[base] += 1
        key = base if claimed[base] == 1 else f"{base}-{claimed[base]}"
        bind.execute(
            sa.text("UPDATE user_profiles SET display_name_key = :key WHERE user_id = :user_id"),
            {"key": key, "user_id": user_id},
        )


def downgrade() -> None:
    # Keys stay unique; rolling back the fold is not needed for schema compatibility.
    pass
