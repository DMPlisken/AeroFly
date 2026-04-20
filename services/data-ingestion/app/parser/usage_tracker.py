"""Records every outbound LLM API call into `ingest.api_usage`.

Design goals
------------
- **Append-only.** One row per call. No updates. No deletes.
- **Defensive.** Tracker never raises into the caller — if the DB write
  fails (e.g. DB down), we log and swallow. The extraction must not be
  aborted because bookkeeping failed.
- **Decoupled.** Accepts a SQLAlchemy session factory at construction so
  the same tracker works from the worker, a CLI script, and tests.
- **No secrets.** Never stores API keys, prompts, or responses. Stores
  only: who, what model, what purpose, how many tokens, how much money.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

from sqlalchemy.orm import Session

from app.db.models import ApiUsage

from .pricing import cost_for_tokens

log = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    provider: str
    model: str
    purpose: str
    aerodrome_icao: str | None = None
    source_chart_id: int | None = None

    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    cache_creation_tokens: int = 0

    latency_ms: int | None = None
    success: bool = True
    error_code: str | None = None
    request_id: str | None = None


class UsageTracker:
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def record(self, usage: UsageRecord) -> int | None:
        """Persist one usage row. Returns the new row id, or None on failure."""
        try:
            costs = cost_for_tokens(
                usage.model,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_input_tokens=usage.cached_input_tokens,
                cache_creation_tokens=usage.cache_creation_tokens,
            )
            session = self._session_factory()
            try:
                row = ApiUsage(
                    provider=usage.provider,
                    model=usage.model,
                    purpose=usage.purpose,
                    aerodrome_icao=usage.aerodrome_icao,
                    source_chart_id=usage.source_chart_id,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cached_input_tokens=usage.cached_input_tokens,
                    cache_creation_tokens=usage.cache_creation_tokens,
                    input_cost_usd=costs["input_cost_usd"],
                    output_cost_usd=costs["output_cost_usd"],
                    cached_input_cost_usd=costs["cached_input_cost_usd"],
                    cache_creation_cost_usd=costs["cache_creation_cost_usd"],
                    total_cost_usd=costs["total_cost_usd"],
                    latency_ms=usage.latency_ms,
                    success=usage.success,
                    error_code=usage.error_code,
                    request_id=usage.request_id,
                )
                session.add(row)
                session.commit()
                return row.id
            finally:
                session.close()
        except Exception as exc:  # noqa: BLE001 — bookkeeping must not abort extraction
            log.exception("UsageTracker.record failed: %s", exc)
            return None
