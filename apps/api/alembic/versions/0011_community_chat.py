"""Community chat conversation type.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE conversations_type_enum ADD VALUE IF NOT EXISTS 'COMMUNITY'")


def downgrade() -> None:
    # PostgreSQL cannot drop a single enum label. The value disappears when 0006 drops the type.
    pass
