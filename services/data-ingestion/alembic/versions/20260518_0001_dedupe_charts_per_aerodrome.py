"""Dedupe duplicate ingest.charts rows per (aerodrome_icao, title).

Fix-up for BUG-013. Before this migration, `manifest_import.py`
deduplicated charts via `source_url`, which embeds the AIRAC edition
slug. Re-running the sync over an AIRAC change therefore left the old
rows in place AND inserted the new ones — chart counts doubled on the
detail page.

This migration cleans up existing duplicates:

- For each `(aerodrome_icao, title)` group, KEEP the row with the
  highest `source_airac_cycle` (so we converge on the most-recent
  edition for that document).
- If any sibling in the group has a non-zero `rotation_degrees`,
  promote that value onto the surviving row (preserves the user's
  per-chart rotation regardless of which version we keep).
- Delete every other sibling.

Idempotent: re-running the migration after the fix is a no-op because
no duplicates remain.

Revision ID: 20260518_0001
Revises: 20260426_0001
Create Date: 2026-05-18
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "20260518_0001"
down_revision: Union[str, None] = "20260426_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "ingest"


def upgrade() -> None:
    # 1. For groups with any non-zero rotation, propagate the max value
    #    onto every row in the group BEFORE we delete duplicates. This is
    #    safe because the survivor in step 2 is selected with rotation
    #    promotion already applied.
    op.execute(
        f"""
        UPDATE {SCHEMA}.charts AS c
        SET rotation_degrees = sub.max_rot
        FROM (
            SELECT aerodrome_icao, title, MAX(rotation_degrees) AS max_rot
            FROM {SCHEMA}.charts
            GROUP BY aerodrome_icao, title
            HAVING MAX(rotation_degrees) > 0
              AND COUNT(*) > 1
        ) AS sub
        WHERE c.aerodrome_icao = sub.aerodrome_icao
          AND c.title = sub.title
          AND c.rotation_degrees <> sub.max_rot;
        """
    )

    # 2. Delete every sibling except the row with the highest
    #    source_airac_cycle per (aerodrome_icao, title). NULL airac sorts
    #    last (oldest) — those rows are pre-AIRAC imports and shouldn't
    #    outrank an explicit cycle.
    op.execute(
        f"""
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY aerodrome_icao, title
                       ORDER BY source_airac_cycle DESC NULLS LAST, id DESC
                   ) AS rn
            FROM {SCHEMA}.charts
        )
        DELETE FROM {SCHEMA}.charts
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1);
        """
    )


def downgrade() -> None:
    # No-op. The duplicates we removed had no semantic value and we
    # cannot reconstruct them from the surviving rows alone.
    pass
