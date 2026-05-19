"""End-to-end aerodrome sync orchestration.

A single sync job moves through three phases for one ICAO:

1. **Scrape** — HTTP call to the sidecar `scraper` service, which uses
   Playwright + Chromium to refresh the chart PNGs + manifest on the
   shared `data/aerodromes/<ICAO>/` volume.
2. **Import** — read the refreshed manifest and upsert aerodrome + chart
   rows into the `ingest` schema (idempotent).
3. **Extract** — re-run the existing 2-of-2 LLM consensus pipeline over
   the (possibly new) charts to refresh structured fields.

Implementation re-uses the existing `ExtractionJob` row: each phase
updates `current_step` so the UI shows where we are without needing a
new DB column.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ExtractionJob
from app.parser.providers.base import ExtractionProvider
from app.services.extraction_runner import ExtractionRunner
from app.services.manifest_import import import_one_manifest

log = logging.getLogger(__name__)

_SCRAPE_POLL_INTERVAL_SECONDS = 5
_SCRAPE_MAX_WAIT_SECONDS = 600  # 10 minutes — generous for the first-time index rebuild
_HTTP_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class SyncPipeline:
    """Runs the full scrape → import → extract sequence for one aerodrome."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        providers: list[ExtractionProvider],
        scraper_url: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._providers = providers
        self._scraper_url = (scraper_url or settings.scraper_url).rstrip("/")

    # ------------------------------------------------------------------ #
    # Public entry — async, called from FastAPI BackgroundTasks
    # ------------------------------------------------------------------ #

    async def run(self, job_id: UUID, icao: str) -> None:
        icao = icao.upper()
        try:
            self._update_job(job_id, status="running", step="Karten werden geladen…", progress=5)
            scrape_summary = await self._scrape(icao)
            self._update_job(job_id, step="Karten werden importiert…", progress=35)
            import_summary = self._import(icao)
            log.info("sync %s scrape=%s import=%s", icao, scrape_summary, import_summary)
        except Exception as exc:  # noqa: BLE001
            log.exception("sync pipeline pre-extract failed for %s", icao)
            self._fail_job(job_id, exc)
            return

        # Hand off to the existing extraction runner (sync code). Run it in
        # a worker thread so we don't block the asyncio loop. The runner
        # itself updates current_step / progress in the same row.
        self._update_job(job_id, step="Felder werden extrahiert…", progress=55)
        runner = ExtractionRunner(
            session_factory=self._session_factory,
            providers=self._providers,
        )
        try:
            await asyncio.to_thread(runner.run, job_id, icao)
        except Exception as exc:  # noqa: BLE001
            log.exception("extraction phase failed for %s", icao)
            self._fail_job(job_id, exc)

    # ------------------------------------------------------------------ #
    # Phases
    # ------------------------------------------------------------------ #

    async def _scrape(self, icao: str) -> dict[str, Any]:
        # Per-request client (no kept-alive pool). Connection re-use across a
        # 5 s `asyncio.sleep` runs straight into uvicorn's default 5 s
        # keep-alive timeout on the scraper side — the pooled connection
        # gets evicted exactly when we want to use it again, and httpx
        # raises ReadError. Opening a fresh client per request avoids
        # the race entirely; the overhead is trivial compared to the
        # multi-minute scrape itself.
        async def _post_start() -> dict:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, base_url=self._scraper_url) as client:
                response = await client.post(f"/scrape/{icao}")
                response.raise_for_status()
                return response.json()

        async def _poll(scrape_job_id: str) -> dict:
            # Best-effort retry on transient connection errors (network blip,
            # keep-alive race). Lets a single hiccup not abort a 2-minute scrape.
            last_exc: Exception | None = None
            for attempt in range(3):
                try:
                    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, base_url=self._scraper_url) as client:
                        resp = await client.get(f"/scrape/jobs/{scrape_job_id}")
                        resp.raise_for_status()
                        return resp.json()
                except (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError) as exc:
                    last_exc = exc
                    log.warning(
                        "scrape poll attempt %d for %s failed (%s); retrying",
                        attempt + 1, scrape_job_id, exc.__class__.__name__,
                    )
                    await asyncio.sleep(2)
            raise RuntimeError(
                f"scrape poll failed 3× for {scrape_job_id}: {last_exc!r}"
            )

        kickoff = await _post_start()
        scrape_job_id = kickoff["id"]

        deadline = asyncio.get_event_loop().time() + _SCRAPE_MAX_WAIT_SECONDS
        while True:
            if asyncio.get_event_loop().time() > deadline:
                raise TimeoutError(
                    f"scrape job {scrape_job_id} did not finish within "
                    f"{_SCRAPE_MAX_WAIT_SECONDS}s"
                )
            await asyncio.sleep(_SCRAPE_POLL_INTERVAL_SECONDS)
            state = await _poll(scrape_job_id)
            if state["status"] == "completed":
                return state.get("result") or {}
            if state["status"] == "failed":
                raise RuntimeError(
                    f"scraper service reported failure: {state.get('error') or 'unknown'}"
                )

    def _import(self, icao: str) -> dict[str, Any]:
        session = self._session_factory()
        try:
            summary = import_one_manifest(icao, session)
            session.commit()
            return summary
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # Job-row helpers
    # ------------------------------------------------------------------ #

    def _update_job(
        self,
        job_id: UUID,
        *,
        status: str | None = None,
        step: str | None = None,
        progress: int | None = None,
    ) -> None:
        session = self._session_factory()
        try:
            job = session.get(ExtractionJob, job_id)
            if job is None:
                return
            if status is not None:
                job.status = status
                if status == "running" and job.started_at is None:
                    job.started_at = datetime.now(timezone.utc)
            if step is not None:
                job.current_step = step
            if progress is not None:
                job.progress_pct = progress
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _fail_job(self, job_id: UUID, exc: Exception) -> None:
        session = self._session_factory()
        try:
            job = session.get(ExtractionJob, job_id)
            if job is None:
                return
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            job.error = f"{type(exc).__name__}: {exc}"
            job.current_step = "Fehlgeschlagen"
            session.commit()
            log.error("job %s marked failed: %s\n%s", job_id, exc, traceback.format_exc())
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
