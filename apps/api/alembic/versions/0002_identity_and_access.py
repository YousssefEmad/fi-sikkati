"""Identity, access and audit tables.

Creates the Phase 2 schema from database.md §2.1 and §2.9: ``users``, ``user_profiles``,
``user_roles``, ``auth_sessions``, ``email_verification_tokens``, ``password_reset_tokens`` and
``audit_logs``, plus the ``set_updated_at`` trigger used by every mutable table.

``audit_logs`` is append-only: the application role keeps ``INSERT, SELECT`` and loses
``UPDATE, DELETE`` (database.md §8), so no code path — including a bug — can rewrite history.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

APP_ROLE = "fisikkati_app"

account_status = sa.Enum("ACTIVE", "SUSPENDED", "DEACTIVATED", "DELETED", name="users_status_enum")
identity_verification_status = sa.Enum(
    "NOT_SUBMITTED",
    "PENDING",
    "APPROVED",
    "REJECTED",
    name="users_identity_verification_status_enum",
)
user_role = sa.Enum("PASSENGER", "DRIVER", "ADMIN", name="user_roles_role_enum")
revoked_reason = sa.Enum(
    "LOGOUT",
    "ROTATED",
    "REUSE_DETECTED",
    "PASSWORD_CHANGED",
    "PASSWORD_RESET",
    "USER_REVOKED",
    "ACCOUNT_CLOSED",
    name="auth_sessions_revoked_reason_enum",
)
actor_type = sa.Enum("USER", "ADMIN", "SYSTEM", name="audit_logs_actor_type_enum")

UPDATED_AT_TABLES = ("users", "user_profiles", "auth_sessions")


def _create_users() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("phone_e164", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("status", account_status, server_default="ACTIVE", nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "identity_verification_status",
            identity_verification_status,
            server_default="NOT_SUBMITTED",
            nullable=False,
        ),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("terms_version", sa.Text(), nullable=False),
        sa.Column("privacy_version", sa.Text(), nullable=False),
        sa.Column("legal_accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locale", sa.Text(), server_default="ar", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("anonymised_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("locale IN ('ar', 'en')", name="ck_users_locale_supported"),
        sa.CheckConstraint(
            "phone_e164 IS NULL OR phone_e164 ~ '^\\+[1-9][0-9]{7,14}$'",
            name="ck_users_phone_e164_format",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("phone_e164", name="uq_users_phone_e164"),
    )
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index(
        "ix_users_deletion_requested_at",
        "users",
        ["deletion_requested_at"],
        postgresql_where=sa.text("deletion_requested_at IS NOT NULL"),
    )


def _create_profiles_and_roles() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "char_length(display_name) BETWEEN 2 AND 60",
            name="ck_user_profiles_display_name_length",
        ),
        sa.CheckConstraint(
            "char_length(full_name) BETWEEN 2 AND 120", name="ck_user_profiles_full_name_length"
        ),
        sa.CheckConstraint(
            "bio IS NULL OR char_length(bio) <= 300", name="ck_user_profiles_bio_length"
        ),
        sa.CheckConstraint(
            "city IS NULL OR char_length(city) <= 80", name="ck_user_profiles_city_length"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_profiles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_profiles"),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("granted_by", sa.Uuid(), nullable=True),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"], ["users.id"], name="fk_user_roles_granted_by_users", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_roles_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "role", name="pk_user_roles"),
    )


def _create_sessions_and_tokens() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("refresh_token_hash", sa.Text(), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_hash", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", revoked_reason, nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_auth_sessions_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auth_sessions"),
        sa.UniqueConstraint("refresh_token_hash", name="uq_auth_sessions_refresh_token_hash"),
    )
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])
    op.create_index("ix_auth_sessions_family_id", "auth_sessions", ["family_id"])
    op.create_index(
        "ix_auth_sessions_user_id_active",
        "auth_sessions",
        ["user_id"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    for table in ("email_verification_tokens", "password_reset_tokens"):
        op.create_table(
            table,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("token_hash", sa.Text(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["user_id"], ["users.id"], name=f"fk_{table}_user_id_users", ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
            sa.UniqueConstraint("token_hash", name=f"uq_{table}_token_hash"),
        )
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])


def _create_audit_logs() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", actor_type, nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("ip_hash", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_audit_logs_actor_id_users", ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_actor_id_created_at", "audit_logs", ["actor_id", "created_at"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_target", "audit_logs", ["target_type", "target_id"])


def _create_updated_at_trigger() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$
        """
    )
    for table in UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def _restrict_audit_log_writes() -> None:
    """Make ``audit_logs`` append-only for the application role (database.md §8).

    Skipped when the role does not exist (e.g. a CI container running everything as superuser);
    the production role is provisioned by the platform.
    """
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
                REVOKE UPDATE, DELETE, TRUNCATE ON TABLE audit_logs FROM {APP_ROLE};
                GRANT INSERT, SELECT ON TABLE audit_logs TO {APP_ROLE};
            END IF;
        END
        $$
        """
    )


def upgrade() -> None:
    _create_users()
    _create_profiles_and_roles()
    _create_sessions_and_tokens()
    _create_audit_logs()
    _create_updated_at_trigger()
    _restrict_audit_log_writes()


def downgrade() -> None:
    for table in UPDATED_AT_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    op.drop_table("audit_logs")
    op.drop_table("password_reset_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_table("auth_sessions")
    op.drop_table("user_roles")
    op.drop_table("user_profiles")
    op.drop_table("users")

    bind = op.get_bind()
    for enum in (
        actor_type,
        revoked_reason,
        user_role,
        identity_verification_status,
        account_status,
    ):
        enum.drop(bind, checkfirst=True)
