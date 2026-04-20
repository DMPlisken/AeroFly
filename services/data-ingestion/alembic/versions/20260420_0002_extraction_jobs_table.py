"""extraction_jobs table for async per-aerodrome extraction tracking.

Revision ID: 20260420_0002
Revises: 20260420_0001
Create Date: 2026-04-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260420_0002"
down_revision: Union[str, None] = "20260420_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "ingest"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "extraction_jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("aerodrome_icao", sa.CHAR(length=4), nullable=False),
        # queued -> running -> (completed | failed)
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_step", sa.String(length=200), nullable=True),
        sa.Column(
            "field_groups_completed",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("fields_written", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_extraction_jobs_icao_created_at",
        "extraction_jobs",
        ["aerodrome_icao", "created_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_extraction_jobs_status",
        "extraction_jobs",
        ["status"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_extraction_jobs_status", table_name="extraction_jobs", schema=SCHEMA)
    op.drop_index(
        "ix_extraction_jobs_icao_created_at",
        table_name="extraction_jobs",
        schema=SCHEMA,
    )
    op.drop_table("extraction_jobs", schema=SCHEMA)
