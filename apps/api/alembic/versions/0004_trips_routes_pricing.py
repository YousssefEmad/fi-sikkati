"""Trips, routes, stops and the initial pricing rule.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-02
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography, Geometry

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

trip_status = sa.Enum(
    "DRAFT",
    "PUBLISHED",
    "FULL",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
    "EXPIRED",
    name="trips_status_enum",
)
stop_kind = sa.Enum("ORIGIN", "WAYPOINT", "DESTINATION", name="trip_stops_kind_enum")
cancelled_by = sa.Enum("DRIVER", "ADMIN", "SYSTEM", name="trips_cancelled_by_enum")

UPDATED_AT_TABLES = ("pricing_rules", "trips", "trip_routes", "trip_stops")


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
        "pricing_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False, server_default="EGP"),
        sa.Column("base_fee_minor", sa.BigInteger(), nullable=False),
        sa.Column("per_km_minor", sa.BigInteger(), nullable=False),
        sa.Column("platform_fee_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("base_fee_minor >= 0", name="ck_pricing_rules_base_fee_non_negative"),
        sa.CheckConstraint("per_km_minor >= 0", name="ck_pricing_rules_per_km_non_negative"),
        sa.CheckConstraint(
            "platform_fee_bps >= 0 AND platform_fee_bps <= 10000",
            name="ck_pricing_rules_platform_fee_bps_range",
        ),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_pricing_rules_currency_iso"),
        sa.PrimaryKeyConstraint("id", name="pk_pricing_rules"),
    )
    op.create_index("ix_pricing_rules_effective_from", "pricing_rules", ["effective_from"])
    op.execute(
        """
        ALTER TABLE pricing_rules ADD CONSTRAINT pricing_rules_effective_range_excl
        EXCLUDE USING gist (
            tstzrange(effective_from, COALESCE(effective_to, 'infinity'::timestamptz), '[)')
            WITH &&
        )
        """
    )
    op.execute(
        """
        INSERT INTO pricing_rules (
            id, name, currency, base_fee_minor, per_km_minor, platform_fee_bps,
            effective_from, created_at, updated_at
        ) VALUES (
            '01924000-aaaa-7000-8000-000000000001',
            'MVP concept (MEP §32)',
            'EGP', 1000, 300, 0,
            TIMESTAMPTZ '2020-01-01 00:00:00+00',
            now(), now()
        )
        """
    )

    op.create_table(
        "trips",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("status", trip_status, nullable=False, server_default="DRAFT"),
        sa.Column("departure_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estimated_arrival_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_seats", sa.Integer(), nullable=False),
        sa.Column("available_seats", sa.Integer(), nullable=False),
        sa.Column("origin_label", sa.Text(), nullable=False),
        sa.Column("destination_label", sa.Text(), nullable=False),
        sa.Column("origin_point", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("destination_point", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("origin_area_point", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column(
            "destination_area_point", Geography(geometry_type="POINT", srid=4326), nullable=False
        ),
        sa.Column("pricing_rule_id", sa.Uuid(), nullable=True),
        sa.Column("price_per_seat_minor", sa.BigInteger(), nullable=True),
        sa.Column("platform_fee_minor", sa.BigInteger(), nullable=True),
        sa.Column("driver_amount_minor", sa.BigInteger(), nullable=True),
        sa.Column("currency", sa.Text(), nullable=False, server_default="EGP"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", cancelled_by, nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("total_seats >= 1", name="ck_trips_total_seats_positive"),
        sa.CheckConstraint(
            "available_seats >= 0 AND available_seats <= total_seats",
            name="ck_trips_available_seats_range",
        ),
        sa.CheckConstraint(
            "estimated_arrival_at > departure_at", name="ck_trips_arrival_after_departure"
        ),
        sa.CheckConstraint("char_length(notes) <= 500", name="ck_trips_notes_length"),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_trips_currency_iso"),
        sa.CheckConstraint("version >= 1", name="ck_trips_version_positive"),
        sa.ForeignKeyConstraint(
            ["driver_id"], ["users.id"], name="fk_trips_driver_id_users", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name="fk_trips_vehicle_id_vehicles",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pricing_rule_id"],
            ["pricing_rules.id"],
            name="fk_trips_pricing_rule_id_pricing_rules",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trips"),
    )
    op.create_index("ix_trips_status_departure_at", "trips", ["status", "departure_at"])
    op.create_index("ix_trips_driver_id_departure_at", "trips", ["driver_id", "departure_at"])
    op.execute("CREATE INDEX ix_trips_origin_point ON trips USING gist (origin_point)")
    op.execute("CREATE INDEX ix_trips_destination_point ON trips USING gist (destination_point)")
    op.create_index(
        "ix_trips_published_departure",
        "trips",
        ["departure_at"],
        postgresql_where=sa.text("status IN ('PUBLISHED', 'FULL')"),
    )
    op.create_index(
        "uq_trips_driver_idempotency_key",
        "trips",
        ["driver_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "trip_routes",
        sa.Column("trip_id", sa.Uuid(), nullable=False),
        sa.Column("geometry", Geometry(geometry_type="LINESTRING", srid=4326), nullable=False),
        sa.Column("corridor", Geography(geometry_type="POLYGON", srid=4326), nullable=False),
        sa.Column("distance_m", sa.Integer(), nullable=False),
        sa.Column("duration_s", sa.Integer(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("provider_ref", sa.Text(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("distance_m >= 0", name="ck_trip_routes_distance_non_negative"),
        sa.CheckConstraint("duration_s >= 0", name="ck_trip_routes_duration_non_negative"),
        sa.ForeignKeyConstraint(
            ["trip_id"], ["trips.id"], name="fk_trip_routes_trip_id_trips", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("trip_id", name="pk_trip_routes"),
    )
    op.execute("CREATE INDEX ix_trip_routes_corridor ON trip_routes USING gist (corridor)")
    op.execute("CREATE INDEX ix_trip_routes_geometry ON trip_routes USING gist (geometry)")

    op.create_table(
        "trip_stops",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trip_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("kind", stop_kind, nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("point", Geography(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("route_fraction", sa.Numeric(6, 5), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "route_fraction >= 0 AND route_fraction <= 1",
            name="ck_trip_stops_route_fraction_range",
        ),
        sa.ForeignKeyConstraint(
            ["trip_id"], ["trips.id"], name="fk_trip_stops_trip_id_trips", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_trip_stops"),
        sa.UniqueConstraint("trip_id", "sequence", name="uq_trip_stops_trip_id_sequence"),
    )

    for table in UPDATED_AT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table}_updated_at BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
        )


def downgrade() -> None:
    for table in UPDATED_AT_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table}")
    op.drop_table("trip_stops")
    op.drop_table("trip_routes")
    op.drop_index("uq_trips_driver_idempotency_key", table_name="trips")
    op.drop_index("ix_trips_published_departure", table_name="trips")
    op.execute("DROP INDEX IF EXISTS ix_trips_destination_point")
    op.execute("DROP INDEX IF EXISTS ix_trips_origin_point")
    op.drop_index("ix_trips_driver_id_departure_at", table_name="trips")
    op.drop_index("ix_trips_status_departure_at", table_name="trips")
    op.drop_table("trips")
    op.execute(
        "ALTER TABLE pricing_rules DROP CONSTRAINT IF EXISTS pricing_rules_effective_range_excl"
    )
    op.drop_index("ix_pricing_rules_effective_from", table_name="pricing_rules")
    op.drop_table("pricing_rules")
    bind = op.get_bind()
    for enum in (cancelled_by, stop_kind, trip_status):
        enum.drop(bind, checkfirst=True)
