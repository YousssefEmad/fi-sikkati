"""Files, identity documents, driver verifications and vehicles.

Creates the Phase 3 schema from database.md §2.2 and adds ``user_profiles.photo_file_id``.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

stored_files_bucket = sa.Enum("PUBLIC_MEDIA", "PRIVATE_DOCUMENTS", name="stored_files_bucket_enum")
stored_files_scan = sa.Enum(
    "NOT_SCANNED", "CLEAN", "INFECTED", "SCAN_UNAVAILABLE", name="stored_files_scan_status_enum"
)
identity_document_type = sa.Enum(
    "NATIONAL_ID_FRONT",
    "NATIONAL_ID_BACK",
    "SELFIE",
    name="identity_documents_document_type_enum",
)
identity_document_status = sa.Enum(
    "PENDING", "APPROVED", "REJECTED", name="identity_documents_status_enum"
)
driver_verification_status = sa.Enum(
    "PENDING", "APPROVED", "REJECTED", "REVOKED", name="driver_verifications_status_enum"
)
vehicle_type = sa.Enum(
    "SEDAN", "HATCHBACK", "SUV", "VAN", "MINIBUS", "OTHER", name="vehicles_vehicle_type_enum"
)
vehicle_status = sa.Enum("ACTIVE", "INACTIVE", name="vehicles_status_enum")
vehicle_verification_status = sa.Enum(
    "PENDING", "APPROVED", "REJECTED", name="vehicles_verification_status_enum"
)
vehicle_document_type = sa.Enum(
    "REGISTRATION_FRONT",
    "REGISTRATION_BACK",
    "VEHICLE_PHOTO",
    name="vehicle_documents_document_type_enum",
)
vehicle_document_status = sa.Enum(
    "PENDING", "APPROVED", "REJECTED", name="vehicle_documents_status_enum"
)

UPDATED_AT_TABLES = (
    "stored_files",
    "identity_documents",
    "driver_verifications",
    "vehicles",
    "vehicle_documents",
)


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
        "stored_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bucket", stored_files_bucket, nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("original_name", sa.Text(), nullable=False),
        sa.Column(
            "scan_status", stored_files_scan, server_default="SCAN_UNAVAILABLE", nullable=False
        ),
        sa.Column("purge_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_stored_files_owner_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stored_files"),
        sa.UniqueConstraint("object_key", name="uq_stored_files_object_key"),
    )

    op.add_column(
        "user_profiles",
        sa.Column("photo_file_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_user_profiles_photo_file_id_stored_files",
        "user_profiles",
        "stored_files",
        ["photo_file_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "identity_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", identity_document_type, nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("status", identity_document_status, server_default="PENDING", nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status <> 'REJECTED' OR (rejection_reason IS NOT NULL AND char_length(rejection_reason) >= 3)",
            name="ck_identity_documents_rejection_reason_required",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_identity_documents_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["stored_files.id"],
            name="fk_identity_documents_file_id_stored_files",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_identity_documents_reviewed_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_identity_documents"),
    )
    op.create_index("ix_identity_documents_user_id", "identity_documents", ["user_id"])
    op.create_index(
        "ix_identity_documents_status_created_at", "identity_documents", ["status", "created_at"]
    )

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("make", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("color", sa.Text(), nullable=False),
        sa.Column("vehicle_type", vehicle_type, nullable=False),
        sa.Column("seat_capacity", sa.Integer(), nullable=False),
        sa.Column("plate_number", sa.Text(), nullable=False),
        sa.Column("status", vehicle_status, server_default="ACTIVE", nullable=False),
        sa.Column(
            "verification_status",
            vehicle_verification_status,
            server_default="PENDING",
            nullable=False,
        ),
        *_timestamps(),
        sa.CheckConstraint("year >= 1980 AND year <= 2100", name="ck_vehicles_year_range"),
        sa.CheckConstraint(
            "seat_capacity >= 2 AND seat_capacity <= 20", name="ck_vehicles_seat_capacity_range"
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_vehicles_owner_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vehicles"),
    )
    op.create_index("ix_vehicles_owner_user_id", "vehicles", ["owner_user_id"])
    op.create_index(
        "ix_vehicles_verification_pending",
        "vehicles",
        ["verification_status"],
        postgresql_where=sa.text("verification_status = 'PENDING'"),
    )

    op.create_table(
        "vehicle_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", vehicle_document_type, nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("status", vehicle_document_status, server_default="PENDING", nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status <> 'REJECTED' OR (rejection_reason IS NOT NULL AND char_length(rejection_reason) >= 3)",
            name="ck_vehicle_documents_rejection_reason_required",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name="fk_vehicle_documents_vehicle_id_vehicles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["file_id"],
            ["stored_files.id"],
            name="fk_vehicle_documents_file_id_stored_files",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_vehicle_documents_reviewed_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_vehicle_documents"),
    )
    op.create_index("ix_vehicle_documents_vehicle_id", "vehicle_documents", ["vehicle_id"])

    op.create_table(
        "driver_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", driver_verification_status, server_default="PENDING", nullable=False),
        sa.Column("licence_file_id", sa.Uuid(), nullable=False),
        sa.Column("licence_expires_on", sa.Date(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status <> 'REJECTED' OR (rejection_reason IS NOT NULL AND char_length(rejection_reason) >= 3)",
            name="ck_driver_verifications_rejection_reason_required",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_driver_verifications_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["licence_file_id"],
            ["stored_files.id"],
            name="fk_driver_verifications_licence_file_id_stored_files",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name="fk_driver_verifications_vehicle_id_vehicles",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_driver_verifications_reviewed_by_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_driver_verifications"),
    )
    op.create_index("ix_driver_verifications_user_id", "driver_verifications", ["user_id"])
    op.create_index(
        "uq_driver_verifications_user_active",
        "driver_verifications",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'APPROVED')"),
    )

    for table in UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in UPDATED_AT_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")

    op.drop_index("uq_driver_verifications_user_active", table_name="driver_verifications")
    op.drop_index("ix_driver_verifications_user_id", table_name="driver_verifications")
    op.drop_table("driver_verifications")
    op.drop_index("ix_vehicle_documents_vehicle_id", table_name="vehicle_documents")
    op.drop_table("vehicle_documents")
    op.drop_index("ix_vehicles_verification_pending", table_name="vehicles")
    op.drop_index("ix_vehicles_owner_user_id", table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index("ix_identity_documents_status_created_at", table_name="identity_documents")
    op.drop_index("ix_identity_documents_user_id", table_name="identity_documents")
    op.drop_table("identity_documents")
    op.drop_constraint(
        "fk_user_profiles_photo_file_id_stored_files", "user_profiles", type_="foreignkey"
    )
    op.drop_column("user_profiles", "photo_file_id")
    op.drop_table("stored_files")

    bind = op.get_bind()
    for enum in (
        vehicle_document_status,
        vehicle_document_type,
        vehicle_verification_status,
        vehicle_status,
        vehicle_type,
        driver_verification_status,
        identity_document_status,
        identity_document_type,
        stored_files_scan,
        stored_files_bucket,
    ):
        enum.drop(bind, checkfirst=True)
