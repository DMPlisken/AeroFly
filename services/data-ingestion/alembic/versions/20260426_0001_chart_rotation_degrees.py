"""Add rotation_degrees column to ingest.charts.

Stores the user's preferred rotation for displaying a chart in the viewer.
Allowed values: 0, 90, 180, 270 (enforced via CHECK constraint).

Revision ID: 20260426_0001
Revises: 20260420_0002
Create Date: 2026-04-26
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260426_0001"
down_revision: Union[str, None] = "20260420_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "ingest"


def upgrade() -> None:
    op.add_column(
        "charts",
        sa.Column(
            "rotation_degrees",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        schema=SCHEMA,
    )
    op.create_check_constraint(
        "ck_charts_rotation_degrees",
        "charts",
        "rotation_degrees IN (0, 90, 180, 270)",
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint("ck_charts_rotation_degrees", "charts", schema=SCHEMA, type_="check")
    op.drop_column("charts", "rotation_degrees", schema=SCHEMA)
