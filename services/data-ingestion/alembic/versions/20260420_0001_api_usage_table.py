"""Append-only api_usage table for LLM-call cost/token tracking.

Revision ID: 20260420_0001
Revises: 20260419_0001
Create Date: 2026-04-20
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260420_0001"
down_revision: Union[str, None] = "20260419_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "ingest"


def upgrade() -> None:
    op.create_table(
        "api_usage",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("purpose", sa.String(length=80), nullable=False),
        sa.Column("aerodrome_icao", sa.CHAR(length=4), nullable=True),
        sa.Column("source_chart_id", sa.BigInteger(), nullable=True),
        # Token counts (may be zero when unknown / cached).
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cached_input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cache_creation_tokens", sa.Integer(), nullable=False, server_default="0"),
        # Cost in USD, 6 dp to capture sub-cent precision on caching discounts.
        sa.Column("input_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("output_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("cached_input_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("cache_creation_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        # Call-level metadata.
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("request_id", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(
            ["source_chart_id"],
            [f"{SCHEMA}.charts.id"],
            ondelete="SET NULL",
            name="fk_api_usage_chart",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_api_usage_created_at", "api_usage", ["created_at"], schema=SCHEMA)
    op.create_index(
        "ix_api_usage_provider_created_at",
        "api_usage",
        ["provider", "created_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_api_usage_icao_created_at",
        "api_usage",
        ["aerodrome_icao", "created_at"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_api_usage_icao_created_at", table_name="api_usage", schema=SCHEMA)
    op.drop_index("ix_api_usage_provider_created_at", table_name="api_usage", schema=SCHEMA)
    op.drop_index("ix_api_usage_created_at", table_name="api_usage", schema=SCHEMA)
    op.drop_table("api_usage", schema=SCHEMA)
