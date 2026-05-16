"""Create gateway.favorites table.

Anonymous, per-device aerodrome bookmarks. No login, no user table — the
client generates a UUID v4 once, stores it in localStorage, and sends it as
the `X-Device-Id` header on every favorites request.

Revision ID: 20260516_0002
Revises: 20260419_0001
Create Date: 2026-05-16
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260516_0002"
down_revision: Union[str, None] = "20260419_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "gateway"
TABLE = "favorites"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("icao", sa.String(length=8), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("device_id", "icao", name="pk_favorites"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_favorites_device_id",
        TABLE,
        ["device_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_favorites_device_id", table_name=TABLE, schema=SCHEMA)
    op.drop_table(TABLE, schema=SCHEMA)
