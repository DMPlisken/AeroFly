"""Bulk per-favorite sync orchestration.

Phase 2 of #69. A single bulk request kicks off a sync for many ICAOs;
the orchestrator processes them **sequentially** through the existing
`SyncPipeline` so that we don't:

- Hammer DFS with parallel scrape requests (politeness).
- Run multiple Playwright contexts in the scraper container at once
  (in-memory job_store is single-process; concurrent calls would still
  serialise inside Chromium and just add memory pressure).
- Exhaust LLM rate limits on the extraction phase.

Each ICAO gets its own `ExtractionJob` row, so the frontend can poll
per-aerodrome status as it already does for single syncs — the only
new client-facing piece is a batch poller endpoint to avoid N round
trips.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ExtractionJob
from app.parser.providers.base import ExtractionProvider
from app.services.sync_pipeline import SyncPipeline

log = logging.getLogger(__name__)


class BulkSync:
    """Runs SyncPipeline.run for each ICAO in sequence."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        providers: list[ExtractionProvider],
        scraper_url: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._providers = providers
        self._scraper_url = scraper_url or settings.scraper_url

    async def run(self, jobs: list[tuple[UUID, str]]) -> None:
        """Process (job_id, icao) pairs sequentially.

        Failure of one job does not abort the rest — each is reported on
        its own row.
        """
        pipeline = SyncPipeline(
            session_factory=self._session_factory,
            providers=self._providers,
            scraper_url=self._scraper_url,
        )
        for job_id, icao in jobs:
            try:
                await pipeline.run(job_id, icao)
            except asyncio.CancelledError:
                log.warning("bulk sync cancelled mid-flight at %s", icao)
                raise
            except Exception:  # noqa: BLE001
                log.exception("bulk sync: %s failed; continuing with next icao", icao)
