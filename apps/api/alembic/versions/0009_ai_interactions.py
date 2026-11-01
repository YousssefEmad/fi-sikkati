"""AI interaction log.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

outcome = sa.Enum(
    "ANSWERED",
    "REFUSED",
    "ERROR",
    name="ai_interactions_outcome_enum",
    create_constraint=False,
)


def upgrade() -> None:
    op.create_table(
        "ai_interactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("prompt_hash", sa.Text(), nullable=False),
        sa.Column(
            "tool_calls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("outcome", outcome, nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_interactions_user_id_created_at",
        "ai_interactions",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_interactions_user_id_created_at", table_name="ai_interactions")
    op.drop_table("ai_interactions")
    outcome.drop(op.get_bind(), checkfirst=True)
