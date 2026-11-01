"""Ratings, reports, blocks and moderation actions.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

report_target = sa.Enum("USER", "TRIP", "MESSAGE", name="reports_target_type_enum")
report_reason = sa.Enum(
    "SAFETY", "HARASSMENT", "SPAM", "NO_SHOW", "FRAUD", "OTHER", name="reports_reason_enum"
)
report_status = sa.Enum("OPEN", "UNDER_REVIEW", "RESOLVED", "DISMISSED", name="reports_status_enum")
moderation_action = sa.Enum(
    "WARN",
    "REMOVE_CONTENT",
    "SUSPEND_USER",
    "RESTORE_USER",
    "CANCEL_TRIP",
    "REVOKE_DRIVER",
    name="moderation_actions_action_enum",
)

UPDATED_AT_TABLES = ("reports", "user_blocks")


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
        "ratings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trip_id", sa.Uuid(), nullable=False),
        sa.Column("rater_id", sa.Uuid(), nullable=False),
        sa.Column("ratee_id", sa.Uuid(), nullable=False),
        sa.Column("overall", sa.SmallInteger(), nullable=False),
        sa.Column("punctuality", sa.SmallInteger(), nullable=True),
        sa.Column("communication", sa.SmallInteger(), nullable=True),
        sa.Column("experience", sa.SmallInteger(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("rater_id <> ratee_id", name="ck_ratings_rater_not_ratee"),
        sa.CheckConstraint("overall BETWEEN 1 AND 5", name="ck_ratings_overall_range"),
        sa.CheckConstraint(
            "punctuality IS NULL OR punctuality BETWEEN 1 AND 5",
            name="ck_ratings_punctuality_range",
        ),
        sa.CheckConstraint(
            "communication IS NULL OR communication BETWEEN 1 AND 5",
            name="ck_ratings_communication_range",
        ),
        sa.CheckConstraint(
            "experience IS NULL OR experience BETWEEN 1 AND 5",
            name="ck_ratings_experience_range",
        ),
        sa.CheckConstraint(
            "comment IS NULL OR char_length(comment) <= 500", name="ck_ratings_comment_length"
        ),
        sa.ForeignKeyConstraint(
            ["trip_id"], ["trips.id"], name="fk_ratings_trip_id_trips", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["rater_id"], ["users.id"], name="fk_ratings_rater_id_users", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["ratee_id"], ["users.id"], name="fk_ratings_ratee_id_users", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ratings"),
        sa.UniqueConstraint("trip_id", "rater_id", "ratee_id", name="uq_ratings_trip_pair"),
    )
    op.create_index("ix_ratings_ratee_id", "ratings", ["ratee_id"])
    op.create_index("ix_ratings_trip_id", "ratings", ["trip_id"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", report_target, nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("reason", report_reason, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", report_status, nullable=False, server_default="OPEN"),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "description IS NULL OR char_length(description) <= 1000",
            name="ck_reports_description_length",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["users.id"],
            name="fk_reports_reporter_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["users.id"],
            name="fk_reports_resolved_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reports"),
    )
    op.create_index(
        "uq_reports_open_target",
        "reports",
        ["reporter_id", "target_type", "target_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('OPEN', 'UNDER_REVIEW')"),
    )
    op.create_index("ix_reports_status_created", "reports", ["status", "created_at"])
    op.create_index("ix_reports_target", "reports", ["target_type", "target_id"])

    op.create_table(
        "moderation_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", moderation_action, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            name="fk_moderation_actions_report_id_reports",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_moderation_actions_actor_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name="fk_moderation_actions_target_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_moderation_actions"),
    )
    op.create_index(
        "ix_moderation_actions_target_user_id", "moderation_actions", ["target_user_id"]
    )

    op.create_table(
        "user_blocks",
        sa.Column("blocker_id", sa.Uuid(), nullable=False),
        sa.Column("blocked_id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("blocker_id <> blocked_id", name="ck_user_blocks_not_self"),
        sa.ForeignKeyConstraint(
            ["blocker_id"],
            ["users.id"],
            name="fk_user_blocks_blocker_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["blocked_id"],
            ["users.id"],
            name="fk_user_blocks_blocked_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("blocker_id", "blocked_id", name="pk_user_blocks"),
        sa.UniqueConstraint("blocker_id", "blocked_id", name="uq_user_blocks_pair"),
    )
    op.create_index("ix_user_blocks_blocked_id", "user_blocks", ["blocked_id"])

    for table in UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in UPDATED_AT_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
    op.drop_table("user_blocks")
    op.drop_table("moderation_actions")
    op.drop_table("reports")
    op.drop_table("ratings")
    bind = op.get_bind()
    moderation_action.drop(bind, checkfirst=True)
    report_status.drop(bind, checkfirst=True)
    report_reason.drop(bind, checkfirst=True)
    report_target.drop(bind, checkfirst=True)
