"""Initial search schema — baseline only.

Creates the `search` PostgreSQL schema. Projection tables (denormalized
mirrors of `ingest` rows) arrive when the Meilisearch sync track starts.

Revision ID: 20260419_0001
Revises:
Create Date: 2026-04-19
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260419_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "search"


def upgrade() -> None:
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"')


def downgrade() -> None:
    # No-op: baseline migration created only the schema (which still holds
    # alembic_version). Drop the schema manually with CASCADE if a clean
    # slate is required.
    pass
