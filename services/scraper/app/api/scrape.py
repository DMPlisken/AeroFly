"""HTTP API for the scraper service.

Public surface:
- `POST /scrape/{icao}?edition=<slug>` — kick off a single-aerodrome scrape.
  If `edition` is omitted, the current AIRAC edition is discovered from
  DFS and used. Returns 202 with a job id.
- `GET  /scrape/jobs/{job_id}` — poll job state.
- `GET  /airac/current` — peek at the auto-discovered current edition.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Query, status

from app.scraper.airac import discover_current_edition
from app.scraper.runner import scrape_one
from app.services.job_store import store

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/airac/current", tags=["airac"], summary="Currently active DFS AIRAC edition")
async def get_current_edition(force_refresh: bool = Query(default=False)) -> dict:
    edition = await discover_current_edition(force_refresh=force_refresh)
    return {"edition": edition}


@router.post(
    "/scrape/{icao}",
    tags=["scrape"],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Kick off a scrape for one aerodrome",
)
async def start_scrape(
    icao: Annotated[str, Path(min_length=4, max_length=4)],
    background: BackgroundTasks,
    edition: str | None = Query(default=None, description="DFS AIRAC edition slug (e.g. 2026MAY15). Auto-discovered if omitted."),
) -> dict:
    icao = icao.upper()
    if edition is None:
        try:
            edition = await discover_current_edition()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=502,
                detail=f"Could not auto-discover AIRAC edition: {exc}",
            ) from exc

    job = await store.create(icao=icao, edition=edition)
    background.add_task(_run_scrape, job.id, icao, edition)
    return job.to_dict()


@router.get("/scrape/jobs/{job_id}", tags=["scrape"], summary="Poll scrape job state")
async def get_scrape_job(job_id: UUID) -> dict:
    job = await store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"scrape job {job_id} not found")
    return job.to_dict()


async def _run_scrape(job_id: UUID, icao: str, edition: str) -> None:
    await store.mark_running(job_id)
    try:
        result = await scrape_one(icao=icao, edition=edition)
        await store.mark_completed(job_id, result=result)
    except asyncio.CancelledError:
        await store.mark_failed(job_id, error="cancelled")
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception("scrape job %s failed", job_id)
        await store.mark_failed(job_id, error=str(exc))
