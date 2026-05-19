"""Async per-aerodrome **sync** trigger (scrape → import → extract).

A sync job goes one further than the legacy `/extract` endpoint: it
first refreshes the scraped chart material from DFS via the sidecar
scraper service, then re-imports the manifest into the DB, then runs
the existing 2-of-2 extraction. The frontend polls the same
ExtractionJob row that was used before; the `current_step` field
carries the phase string for live UI feedback.

Endpoint URL is mounted under `/aerodromes/{icao}/sync` to mirror the
existing `/aerodromes/{icao}/extract` shape — the gateway forwards
both identically.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.api.extraction import _get_providers, _get_session_factory, _job_to_dict, get_db
from app.db.models import Aerodrome, ExtractionJob
from app.services.bulk_sync import BulkSync
from app.services.sync_pipeline import SyncPipeline

log = logging.getLogger(__name__)

router = APIRouter(prefix="/aerodromes", tags=["sync"])


@router.post(
    "/{icao}/sync",
    status_code=202,
    summary="Refresh charts from DFS and re-extract structured fields",
    description=(
        "Three-phase pipeline for one aerodrome: (1) the scraper sidecar "
        "downloads fresh PNGs from DFS BasicVFR, (2) the manifest is imported "
        "into the DB, (3) the existing 2-of-2 LLM consensus extraction runs "
        "over the (possibly new) charts. Returns the ExtractionJob immediately; "
        "the client polls `/extraction/aerodromes/{icao}/latest` for status."
    ),
)
def start_sync(
    icao: Annotated[str, Path(min_length=4, max_length=4)],
    background: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    icao = icao.upper()

    aerodrome = db.get(Aerodrome, icao)
    if aerodrome is None:
        raise HTTPException(status_code=404, detail=f"Aerodrome {icao} not found")

    # Active-job dedup — same logic as POST /extract, but the staleness
    # window is wider because the scrape phase can legitimately take
    # several minutes (especially the first run after AIRAC change which
    # rebuilds the airport index).
    STALE_AFTER = timedelta(minutes=20)
    now = datetime.now(timezone.utc)

    active = db.execute(
        select(ExtractionJob)
        .where(
            ExtractionJob.aerodrome_icao == icao,
            ExtractionJob.status.in_(("queued", "running")),
        )
        .order_by(ExtractionJob.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if active is not None:
        last_activity = active.started_at or active.created_at
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)
        if now - last_activity > STALE_AFTER:
            log.warning(
                "Promoting stale sync job %s on %s to failed (last activity %s ago)",
                active.id, icao, now - last_activity,
            )
            active.status = "failed"
            active.error = (
                f"Stuck for {(now - last_activity).total_seconds():.0f}s without "
                "progress — treated as abandoned, please retry."
            )
            active.completed_at = now
            db.commit()
        else:
            return _job_to_dict(active)

    job = ExtractionJob(
        aerodrome_icao=icao,
        status="queued",
        progress_pct=0,
        current_step="In Warteschlange",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    pipeline = SyncPipeline(
        session_factory=_get_session_factory(),
        providers=_get_providers(),
        scraper_url=settings.scraper_url,
    )
    background.add_task(pipeline.run, job.id, icao)

    return _job_to_dict(job)


class BulkSyncRequest(BaseModel):
    icaos: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="ICAO codes to sync. Processed sequentially.",
    )


@router.post(
    "/sync-bulk",
    status_code=202,
    summary="Sync many aerodromes in one request (sequential)",
    description=(
        "Phase 2 of #69. Creates one ExtractionJob per ICAO and processes "
        "them sequentially via the standard SyncPipeline (DFS politeness + "
        "LLM-rate-limit friendly). Returns the list of created jobs; the "
        "client polls them via `GET /extraction/latest-bulk?icaos=...` or "
        "per-icao."
    ),
)
def start_bulk_sync(
    payload: Annotated[BulkSyncRequest, Body(...)],
    background: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    requested = [code.strip().upper() for code in payload.icaos]
    # Drop duplicates while preserving order — keeps the response and the
    # job list in the order the user sees on the dashboard.
    seen: set[str] = set()
    icaos: list[str] = []
    for code in requested:
        if not code or code in seen:
            continue
        seen.add(code)
        icaos.append(code)
    if not icaos:
        raise HTTPException(status_code=400, detail="icaos must contain at least one valid code")

    # Validate every ICAO exists before kicking off — half-failed bulk
    # runs are confusing.
    found = {
        row.icao
        for row in db.execute(
            select(Aerodrome).where(Aerodrome.icao.in_(icaos))
        ).scalars().all()
    }
    missing = [code for code in icaos if code not in found]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown ICAOs: {', '.join(missing)}",
        )

    # Promote stale active jobs and reuse fresh ones (mirrors single-sync
    # dedup), then create a job row for every ICAO that needs one.
    STALE_AFTER = timedelta(minutes=20)
    now = datetime.now(timezone.utc)
    jobs_to_run: list[tuple[UUID, str]] = []
    out_jobs: list[dict] = []

    for icao in icaos:
        active = db.execute(
            select(ExtractionJob)
            .where(
                ExtractionJob.aerodrome_icao == icao,
                ExtractionJob.status.in_(("queued", "running")),
            )
            .order_by(ExtractionJob.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if active is not None:
            last = active.started_at or active.created_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if now - last > STALE_AFTER:
                active.status = "failed"
                active.error = (
                    f"Stuck for {(now - last).total_seconds():.0f}s without "
                    "progress — treated as abandoned, please retry."
                )
                active.completed_at = now
            else:
                out_jobs.append(_job_to_dict(active))
                continue

        new_job = ExtractionJob(
            aerodrome_icao=icao,
            status="queued",
            progress_pct=0,
            current_step="In Warteschlange (Sammel-Sync)",
        )
        db.add(new_job)
        db.flush()
        jobs_to_run.append((new_job.id, icao))
        out_jobs.append(_job_to_dict(new_job))

    db.commit()

    if jobs_to_run:
        bulk = BulkSync(
            session_factory=_get_session_factory(),
            providers=_get_providers(),
            scraper_url=settings.scraper_url,
        )
        background.add_task(bulk.run, jobs_to_run)

    return {"jobs": out_jobs, "queued": len(jobs_to_run), "total": len(out_jobs)}
