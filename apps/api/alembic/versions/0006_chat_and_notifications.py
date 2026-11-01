"""Trip chat and in-app notifications.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

conversation_type = sa.Enum("TRIP", name="conversations_type_enum")
message_kind = sa.Enum("TEXT", "SYSTEM", name="messages_kind_enum")
notification_type = sa.Enum(
    "JOIN_REQUEST_RECEIVED",
    "JOIN_REQUEST_ACCEPTED",
    "JOIN_REQUEST_REJECTED",
    "JOIN_REQUEST_CANCELLED",
    "TRIP_UPDATED",
    "TRIP_STARTED",
    "TRIP_CANCELLED",
    "TRIP_COMPLETED",
    "TRIP_STARTING_SOON",
    "TRIP_REMINDER",
    "NEW_MESSAGE",
    "NEW_MATCHING_TRIP",
    "VERIFICATION_STATUS_CHANGED",
    "RATING_RECEIVED",
    "REPORT_UPDATED",
    "ACCOUNT_MODERATED",
    "ANNOUNCEMENT",
    name="notifications_type_enum",
)
notification_channel = sa.Enum("IN_APP", "EMAIL", name="notification_preferences_channel_enum")

UPDATED_AT_TABLES = ("conversations", "conversation_members", "notification_preferences")


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
    op.execute("ALTER TYPE user_roles_role_enum ADD VALUE IF NOT EXISTS 'SUPER_ADMIN'")
    op.add_column(
        "user_profiles",
        sa.Column(
            "share_phone_with_trip_peers",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "type",
            conversation_type,
            nullable=False,
            server_default="TRIP",
        ),
        sa.Column("trip_id", sa.Uuid(), nullable=True),
        sa.Column("is_read_only", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_timestamps(),
        sa.CheckConstraint(
            "(type = 'TRIP' AND trip_id IS NOT NULL) OR (type <> 'TRIP' AND trip_id IS NULL)",
            name="ck_conversations_trip_type_has_trip",
        ),
        sa.ForeignKeyConstraint(
            ["trip_id"], ["trips.id"], name="fk_conversations_trip_id_trips", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
        sa.UniqueConstraint("trip_id", name="uq_conversations_trip_id"),
    )

    op.create_table(
        "conversation_members",
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_read_message_id", sa.Uuid(), nullable=True),
        sa.Column("muted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_conversation_members_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_conversation_members_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("conversation_id", "user_id", name="pk_conversation_members"),
    )
    op.create_index(
        "ix_conversation_members_user_active",
        "conversation_members",
        ["user_id"],
        postgresql_where=sa.text("left_at IS NULL"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=True),
        sa.Column("kind", message_kind, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("system_event", sa.Text(), nullable=True),
        sa.Column("client_message_id", sa.Uuid(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(body) BETWEEN 1 AND 2000",
            name="ck_messages_body_length",
        ),
        sa.CheckConstraint(
            "(kind = 'SYSTEM' AND sender_id IS NULL AND system_event IS NOT NULL) OR "
            "(kind = 'TEXT' AND sender_id IS NOT NULL AND system_event IS NULL)",
            name="ck_messages_kind_fields",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_messages_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"], ["users.id"], name="fk_messages_sender_id_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by"], ["users.id"], name="fk_messages_deleted_by_users", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id", "id"])
    op.create_index(
        "uq_messages_sender_client_message",
        "messages",
        ["sender_id", "client_message_id"],
        unique=True,
        postgresql_where=sa.text("client_message_id IS NOT NULL"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedupe_key", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_notifications_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
    )
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id"],
        postgresql_where=sa.text("read_at IS NULL"),
    )
    op.create_index(
        "ix_notifications_email_pending",
        "notifications",
        ["created_at"],
        postgresql_where=sa.text("email_requested_at IS NOT NULL AND email_sent_at IS NULL"),
    )
    op.create_index(
        "uq_notifications_dedupe_key",
        "notifications",
        ["user_id", "dedupe_key"],
        unique=True,
        postgresql_where=sa.text("dedupe_key IS NOT NULL"),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notification_preferences_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "type", "channel", name="pk_notification_preferences"),
    )

    for table in UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in UPDATED_AT_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
    op.drop_table("notification_preferences")
    op.drop_index("uq_notifications_dedupe_key", table_name="notifications")
    op.drop_index("ix_notifications_email_pending", table_name="notifications")
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("uq_messages_sender_client_message", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversation_members_user_active", table_name="conversation_members")
    op.drop_table("conversation_members")
    op.drop_table("conversations")
    op.drop_column("user_profiles", "share_phone_with_trip_peers")
    bind = op.get_bind()
    notification_channel.drop(bind, checkfirst=True)
    notification_type.drop(bind, checkfirst=True)
    message_kind.drop(bind, checkfirst=True)
    conversation_type.drop(bind, checkfirst=True)
    # SUPER_ADMIN cannot be removed from the enum without rewriting the type.
