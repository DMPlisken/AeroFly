"""Initial ingest schema — aerodrome domain tables.

Creates the `ingest` PostgreSQL schema, all enum types, and the six
authoritative tables: airac_cycles, aerodromes, runways, frequencies,
charts, notams.

Revision ID: 20260419_0001
Revises:
Create Date: 2026-04-19
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260419_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "ingest"

# Enum types: all created via raw SQL in upgrade() for deterministic ordering.
# Column references use create_type=False so SQLAlchemy does not re-attempt
# creation during op.create_table().
_ENUM_VALUES: dict[str, tuple[str, ...]] = {
    "aerodrome_type": ("international", "regional", "general_aviation", "military", "private", "other"),
    "runway_surface": ("asphalt", "concrete", "grass", "gravel", "sand", "water", "snow", "other"),
    "frequency_type": ("twr", "gnd", "atis", "afis", "app", "dep", "del", "info",
                       "radio", "cta", "fis", "emergency", "other"),
    "chart_type":     ("ad_info", "ad_chart", "parking", "taxi", "sid", "star", "iac", "vac", "general", "other"),
    "notam_category": ("new", "replace", "cancel"),
    "notam_severity": ("critical", "high", "normal", "low"),
    "notam_traffic":  ("ifr", "vfr", "ifr_vfr", "checklist"),
    "notam_purpose":  ("nbo", "bo", "m", "k"),
    "notam_scope":    ("aerodrome", "en_route", "nav_warning", "checklist"),
}


def _col_enum(name: str) -> postgresql.ENUM:
    """Return an ENUM bound to an existing Postgres type (no create/drop)."""
    return postgresql.ENUM(
        *_ENUM_VALUES[name],
        name=name,
        schema=SCHEMA,
        create_type=False,
    )


AERODROME_TYPE = _col_enum("aerodrome_type")
RUNWAY_SURFACE = _col_enum("runway_surface")
FREQUENCY_TYPE = _col_enum("frequency_type")
CHART_TYPE = _col_enum("chart_type")
NOTAM_CATEGORY = _col_enum("notam_category")
NOTAM_SEVERITY = _col_enum("notam_severity")
NOTAM_TRAFFIC = _col_enum("notam_traffic")
NOTAM_PURPOSE = _col_enum("notam_purpose")
NOTAM_SCOPE = _col_enum("notam_scope")


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')

    # Create all enums via raw SQL; columns below use create_type=False.
    for enum_name, values in _ENUM_VALUES.items():
        values_sql = ", ".join(f"'{v}'" for v in values)
        op.execute(f'CREATE TYPE "{SCHEMA}".{enum_name} AS ENUM ({values_sql})')

    # airac_cycles
    op.create_table(
        "airac_cycles",
        sa.Column("ident", sa.String(length=7), primary_key=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema=SCHEMA,
    )

    # aerodromes
    op.create_table(
        "aerodromes",
        sa.Column("icao", sa.CHAR(length=4), primary_key=True),
        sa.Column("iata", sa.CHAR(length=3), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_de", sa.String(length=200), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("city_de", sa.String(length=120), nullable=True),
        sa.Column("region", sa.String(length=80), nullable=True),
        sa.Column("region_de", sa.String(length=80), nullable=True),
        sa.Column("country", sa.CHAR(length=2), nullable=False, server_default="DE"),
        sa.Column("type", AERODROME_TYPE, nullable=False, server_default="other"),
        sa.Column("operator", sa.String(length=200), nullable=True),
        sa.Column("operator_de", sa.String(length=200), nullable=True),
        sa.Column("latitude", postgresql.DOUBLE_PRECISION(), nullable=True),
        sa.Column("longitude", postgresql.DOUBLE_PRECISION(), nullable=True),
        sa.Column("elevation_ft", sa.Integer(), nullable=True),
        sa.Column("magnetic_variation", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("ref_point_remark", sa.String(length=500), nullable=True),
        sa.Column("ref_point_remark_de", sa.String(length=500), nullable=True),
        sa.Column("source_airac_cycle", sa.String(length=7), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_aerodromes_name", "aerodromes", ["name"], schema=SCHEMA)
    op.create_index("ix_aerodromes_name_de", "aerodromes", ["name_de"], schema=SCHEMA)
    op.create_index("ix_aerodromes_city", "aerodromes", ["city"], schema=SCHEMA)
    op.create_index("ix_aerodromes_type", "aerodromes", ["type"], schema=SCHEMA)
    op.create_index(
        "ix_aerodromes_source_airac_cycle",
        "aerodromes",
        ["source_airac_cycle"],
        schema=SCHEMA,
    )

    # runways
    op.create_table(
        "runways",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("aerodrome_icao", sa.CHAR(length=4), nullable=False),
        sa.Column("designator_le", sa.String(length=4), nullable=False),
        sa.Column("designator_he", sa.String(length=4), nullable=False),
        sa.Column("true_heading_le", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("true_heading_he", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("length_m", sa.Integer(), nullable=True),
        sa.Column("width_m", sa.Integer(), nullable=True),
        sa.Column("surface", RUNWAY_SURFACE, nullable=False, server_default="other"),
        sa.Column("strength", sa.String(length=120), nullable=True),
        sa.Column("le_thr_elevation_ft", sa.Integer(), nullable=True),
        sa.Column("he_thr_elevation_ft", sa.Integer(), nullable=True),
        sa.Column("le_tora_m", sa.Integer(), nullable=True),
        sa.Column("le_toda_m", sa.Integer(), nullable=True),
        sa.Column("le_asda_m", sa.Integer(), nullable=True),
        sa.Column("le_lda_m", sa.Integer(), nullable=True),
        sa.Column("he_tora_m", sa.Integer(), nullable=True),
        sa.Column("he_toda_m", sa.Integer(), nullable=True),
        sa.Column("he_asda_m", sa.Integer(), nullable=True),
        sa.Column("he_lda_m", sa.Integer(), nullable=True),
        sa.Column("ils_le", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ils_he", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.Column("remark_de", sa.String(length=500), nullable=True),
        sa.Column("source_airac_cycle", sa.String(length=7), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["aerodrome_icao"],
            [f"{SCHEMA}.aerodromes.icao"],
            ondelete="CASCADE",
            name="fk_runways_aerodrome",
        ),
        sa.UniqueConstraint(
            "aerodrome_icao",
            "designator_le",
            "designator_he",
            name="uq_runway_designator",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_runways_aerodrome_icao", "runways", ["aerodrome_icao"], schema=SCHEMA
    )
    op.create_index(
        "ix_runways_source_airac_cycle",
        "runways",
        ["source_airac_cycle"],
        schema=SCHEMA,
    )

    # frequencies
    op.create_table(
        "frequencies",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("aerodrome_icao", sa.CHAR(length=4), nullable=False),
        sa.Column("type", FREQUENCY_TYPE, nullable=False),
        sa.Column("callsign", sa.String(length=120), nullable=True),
        sa.Column("callsign_de", sa.String(length=120), nullable=True),
        sa.Column("frequency_mhz", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("remark", sa.String(length=500), nullable=True),
        sa.Column("remark_de", sa.String(length=500), nullable=True),
        sa.Column("operational_hours", sa.String(length=240), nullable=True),
        sa.Column("operational_hours_de", sa.String(length=240), nullable=True),
        sa.Column("source_airac_cycle", sa.String(length=7), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["aerodrome_icao"],
            [f"{SCHEMA}.aerodromes.icao"],
            ondelete="CASCADE",
            name="fk_frequencies_aerodrome",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_frequencies_aerodrome_icao",
        "frequencies",
        ["aerodrome_icao"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_frequencies_aerodrome_type",
        "frequencies",
        ["aerodrome_icao", "type"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_frequencies_source_airac_cycle",
        "frequencies",
        ["source_airac_cycle"],
        schema=SCHEMA,
    )

    # charts
    op.create_table(
        "charts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("aerodrome_icao", sa.CHAR(length=4), nullable=False),
        sa.Column("chart_type", CHART_TYPE, nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("title_de", sa.String(length=300), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("local_path", sa.String(length=1000), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("language", sa.CHAR(length=2), nullable=False, server_default="de"),
        sa.Column("source_airac_cycle", sa.String(length=7), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["aerodrome_icao"],
            [f"{SCHEMA}.aerodromes.icao"],
            ondelete="CASCADE",
            name="fk_charts_aerodrome",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_charts_aerodrome_icao", "charts", ["aerodrome_icao"], schema=SCHEMA)
    op.create_index("ix_charts_chart_type", "charts", ["chart_type"], schema=SCHEMA)
    op.create_index(
        "ix_charts_source_url", "charts", ["source_url"], unique=True, schema=SCHEMA
    )
    op.create_index(
        "ix_charts_source_airac_cycle",
        "charts",
        ["source_airac_cycle"],
        schema=SCHEMA,
    )

    # notams
    op.create_table(
        "notams",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("notam_id", sa.String(length=32), nullable=False),
        sa.Column("aerodrome_icao", sa.CHAR(length=4), nullable=True),
        sa.Column("fir", sa.CHAR(length=4), nullable=True),
        sa.Column("category", NOTAM_CATEGORY, nullable=False, server_default="new"),
        sa.Column("severity", NOTAM_SEVERITY, nullable=False, server_default="normal"),
        sa.Column("q_fir", sa.CHAR(length=4), nullable=True),
        sa.Column("q_code", sa.String(length=5), nullable=True),
        sa.Column("q_traffic", NOTAM_TRAFFIC, nullable=True),
        sa.Column(
            "q_purpose",
            postgresql.ARRAY(NOTAM_PURPOSE),
            nullable=False,
            server_default=sa.text("'{}'::ingest.notam_purpose[]"),
        ),
        sa.Column(
            "q_scope",
            postgresql.ARRAY(NOTAM_SCOPE),
            nullable=False,
            server_default=sa.text("'{}'::ingest.notam_scope[]"),
        ),
        sa.Column("q_lower_limit_ft", sa.Integer(), nullable=True),
        sa.Column("q_upper_limit_ft", sa.Integer(), nullable=True),
        sa.Column("q_coords_lat", postgresql.DOUBLE_PRECISION(), nullable=True),
        sa.Column("q_coords_lon", postgresql.DOUBLE_PRECISION(), nullable=True),
        sa.Column("q_radius_nm", sa.Integer(), nullable=True),
        sa.Column("a_location", sa.CHAR(length=4), nullable=True),
        sa.Column("b_valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("c_valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("d_schedule", sa.String(length=500), nullable=True),
        sa.Column("e_condition", sa.Text(), nullable=False),
        sa.Column("e_condition_de", sa.Text(), nullable=True),
        sa.Column("f_lower_limit", sa.String(length=40), nullable=True),
        sa.Column("g_upper_limit", sa.String(length=40), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("source_airac_cycle", sa.String(length=7), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["aerodrome_icao"],
            [f"{SCHEMA}.aerodromes.icao"],
            ondelete="SET NULL",
            name="fk_notams_aerodrome",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_notams_notam_id", "notams", ["notam_id"], unique=True, schema=SCHEMA
    )
    op.create_index(
        "ix_notams_aerodrome_icao", "notams", ["aerodrome_icao"], schema=SCHEMA
    )
    op.create_index("ix_notams_valid_from", "notams", ["b_valid_from"], schema=SCHEMA)
    op.create_index("ix_notams_severity", "notams", ["severity"], schema=SCHEMA)
    op.create_index(
        "ix_notams_source_airac_cycle",
        "notams",
        ["source_airac_cycle"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_table("notams", schema=SCHEMA)
    op.drop_table("charts", schema=SCHEMA)
    op.drop_table("frequencies", schema=SCHEMA)
    op.drop_table("runways", schema=SCHEMA)
    op.drop_table("aerodromes", schema=SCHEMA)
    op.drop_table("airac_cycles", schema=SCHEMA)

    for enum_name in reversed(list(_ENUM_VALUES.keys())):
        op.execute(f'DROP TYPE IF EXISTS "{SCHEMA}".{enum_name}')

    # Schema itself is retained (alembic_version lives there and is still
    # needed by the migration runner). Drop it manually with CASCADE after
    # downgrade if a clean slate is required.
