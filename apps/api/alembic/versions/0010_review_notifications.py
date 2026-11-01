"""Staff review notifications.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE notifications_type_enum ADD VALUE IF NOT EXISTS 'REVIEW_REQUESTED'")


def downgrade() -> None:
    # PostgreSQL cannot drop a single enum label. The value disappears when 0006 drops the type.
    pass
