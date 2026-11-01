"""Feature flags and app settings for the admin platform.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_table(
        "app_settings",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("key"),
    )
    flags = sa.table(
        "feature_flags",
        sa.column("key", sa.Text()),
        sa.column("enabled", sa.Boolean()),
        sa.column("description", sa.Text()),
    )
    op.bulk_insert(
        flags,
        [
            {
                "key": "ai.enabled",
                "enabled": False,
                "description": "Natural-language trip discovery and FAQ assistant.",
            }
        ],
    )
    settings = sa.table(
        "app_settings",
        sa.column("key", sa.Text()),
        sa.column("value", postgresql.JSONB(astext_type=sa.Text())),
    )
    op.bulk_insert(
        settings,
        [
            {"key": "matching.default_time_window_minutes", "value": {"int": 60}},
            {"key": "trips.max_passenger_seats", "value": {"int": 7}},
            {"key": "ratings.min_count_to_display", "value": {"int": 3}},
            {"key": "reports.auto_hide_threshold", "value": {"int": 3}},
        ],
    )
    op.execute(
        """
        CREATE TRIGGER set_updated_at_feature_flags
        BEFORE UPDATE ON feature_flags
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )
    op.execute(
        """
        CREATE TRIGGER set_updated_at_app_settings
        BEFORE UPDATE ON app_settings
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_updated_at_app_settings ON app_settings")
    op.execute("DROP TRIGGER IF EXISTS set_updated_at_feature_flags ON feature_flags")
    op.drop_table("app_settings")
    op.drop_table("feature_flags")
