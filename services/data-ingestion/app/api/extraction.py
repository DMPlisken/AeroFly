"""Async per-aerodrome extraction trigger + progress polling."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_session_factory
from app.db.models import Aerodrome, ExtractionJob
from app.parser.providers.claude_vision import ClaudeVisionProvider
from app.parser.providers.openai_vision import OpenAIVisionProvider
from app.parser.usage_tracker import UsageTracker
from app.services.extraction_runner import ExtractionRunner

log = logging.getLogger(__name__)

router = APIRouter(prefix="/extraction", tags=["extraction"])

# Singletons — built lazily on first request.
_SessionFactory = None
_Providers: list | None = None


def _get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = get_session_factory(settings.database_url)
    return _SessionFactory


def _get_providers():
    global _Providers
    if _Providers is None:
        tracker = UsageTracker(_get_session_factory())
        _Providers = [
            ClaudeVisionProvider(tracker=tracker),
            OpenAIVisionProvider(tracker=tracker),
        ]
    return _Providers


def get_db():
    session = _get_session_factory()()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _job_to_dict(job: ExtractionJob) -> dict:
    return {
        "id": str(job.id),
        "aerodrome_icao": job.aerodrome_icao,
        "status": job.status,
        "progress_pct": job.progress_pct,
        "current_step": job.current_step,
        "fields_written": job.fields_written,
        "field_groups_completed": job.field_groups_completed or {},
        "created_at": _iso(job.created_at),
        "started_at": _iso(job.started_at),
        "completed_at": _iso(job.completed_at),
        "error": job.error,
    }


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}", summary="Get extraction job state")
def get_job(
    job_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    job = db.get(ExtractionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"extraction job {job_id} not found")
    return _job_to_dict(job)


@router.get(
    "/aerodromes/{icao}/latest",
    summary="Latest extraction job for an aerodrome",
)
def get_latest_job(
    icao: Annotated[str, Path(min_length=4, max_length=4)],
    db: Annotated[Session, Depends(get_db)],
) -> dict | None:
    icao = icao.upper()
    job = db.execute(
        select(ExtractionJob)
        .where(ExtractionJob.aerodrome_icao == icao)
        .order_by(ExtractionJob.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    return _job_to_dict(job) if job else None


# ---------------------------------------------------------------------------
# Kickoff — NOTE: declared on /aerodromes not /extraction to match the user-
# facing URL that the frontend reaches through the gateway proxy.
# ---------------------------------------------------------------------------

trigger_router = APIRouter(prefix="/aerodromes", tags=["extraction"])


@trigger_router.post(
    "/{icao}/extract",
    status_code=202,
    summary="Kick off a 2-of-2 extraction job for one aerodrome",
)
def start_extraction(
    icao: Annotated[str, Path(min_length=4, max_length=4)],
    background: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    icao = icao.upper()

    aerodrome = db.get(Aerodrome, icao)
    if aerodrome is None:
        raise HTTPException(status_code=404, detail=f"Aerodrome {icao} not found")

    # If a job is currently queued or running for this ICAO, return it.
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

    job_id = job.id
    runner = ExtractionRunner(
        session_factory=_get_session_factory(),
        providers=_get_providers(),
    )
    background.add_task(runner.run, job_id, icao)

    return _job_to_dict(job)
