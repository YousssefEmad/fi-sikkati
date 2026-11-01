"""Join requests and the seat-reservation indexes.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

join_status = sa.Enum(
    "PENDING",
    "ACCEPTED",
    "REJECTED",
    "CANCELLED",
    "EXPIRED",
    "COMPLETED",
    name="trip_join_requests_status_enum",
)
join_cancelled_by = sa.Enum(
    "PASSENGER",
    "DRIVER",
    "ADMIN",
    "SYSTEM",
    name="trip_join_requests_cancelled_by_enum",
)

UPDATED_AT_TABLES = ("trip_join_requests",)


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
        "trip_join_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trip_id", sa.Uuid(), nullable=False),
        sa.Column("passenger_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            join_status,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("seats_requested", sa.Integer(), nullable=False),
        sa.Column("pickup_point", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("dropoff_point", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("pickup_label", sa.Text(), nullable=False),
        sa.Column("dropoff_label", sa.Text(), nullable=False),
        sa.Column("pickup_fraction", sa.Numeric(6, 5), nullable=False),
        sa.Column("dropoff_fraction", sa.Numeric(6, 5), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", join_cancelled_by, nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("minutes_before_departure_at_cancel", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("seats_requested >= 1", name="ck_trip_join_requests_seats_positive"),
        sa.CheckConstraint(
            "note IS NULL OR char_length(note) <= 300",
            name="ck_trip_join_requests_note_length",
        ),
        sa.CheckConstraint(
            "pickup_fraction >= 0 AND pickup_fraction <= 1 "
            "AND dropoff_fraction >= 0 AND dropoff_fraction <= 1 "
            "AND pickup_fraction < dropoff_fraction",
            name="ck_trip_join_requests_fractions_ordered",
        ),
        sa.ForeignKeyConstraint(
            ["trip_id"],
            ["trips.id"],
            name="fk_trip_join_requests_trip_id_trips",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["passenger_id"],
            ["users.id"],
            name="fk_trip_join_requests_passenger_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trip_join_requests"),
    )
    op.create_index(
        "uq_trip_join_requests_active_pair",
        "trip_join_requests",
        ["trip_id", "passenger_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'ACCEPTED')"),
    )
    op.create_index(
        "uq_trip_join_requests_passenger_idempotency",
        "trip_join_requests",
        ["passenger_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_trip_join_requests_trip_id_status",
        "trip_join_requests",
        ["trip_id", "status"],
    )
    op.create_index(
        "ix_trip_join_requests_passenger_created",
        "trip_join_requests",
        ["passenger_id", "created_at"],
    )
    op.create_index(
        "ix_trip_join_requests_pending",
        "trip_join_requests",
        ["status", "created_at"],
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    for table in UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in UPDATED_AT_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
    op.drop_index("ix_trip_join_requests_pending", table_name="trip_join_requests")
    op.drop_index("ix_trip_join_requests_passenger_created", table_name="trip_join_requests")
    op.drop_index("ix_trip_join_requests_trip_id_status", table_name="trip_join_requests")
    op.drop_index("uq_trip_join_requests_passenger_idempotency", table_name="trip_join_requests")
    op.drop_index("uq_trip_join_requests_active_pair", table_name="trip_join_requests")
    op.drop_table("trip_join_requests")
    bind = op.get_bind()
    join_cancelled_by.drop(bind, checkfirst=True)
    join_status.drop(bind, checkfirst=True)
