"""AeroFly Data Ingestion — DFS data scraping, parsing & import."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from sqlalchemy import update

from app.api.aerodromes import router as aerodromes_router
from app.api.charts import router as charts_router
from app.api.extraction import router as extraction_router
from app.api.extraction import trigger_router as extraction_trigger_router
from app.api.usage import router as usage_router
from app.core.config import settings
from app.db import get_session_factory
from app.db.models import ExtractionJob

log = logging.getLogger(__name__)


def _sweep_orphaned_jobs() -> int:
    """Mark any queued/running extraction_jobs as failed.

    BackgroundTasks run in-process; a container restart (hot-reload,
    OOM, manual) kills the async runner without updating the DB row.
    Without this sweep the POST /extract endpoint keeps returning the
    orphaned ghost job and the user cannot retry.
    """
    session_factory = get_session_factory(settings.database_url)
    session = session_factory()
    try:
        result = session.execute(
            update(ExtractionJob)
            .where(ExtractionJob.status.in_(("queued", "running")))
            .values(
                status="failed",
                error=(
                    "Worker interrupted (data-ingestion restart); "
                    "run state lost. Please retry."
                ),
                completed_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        swept = result.rowcount or 0
        if swept:
            log.warning("Startup sweep: marked %d orphaned extraction job(s) as failed", swept)
        return swept
    except Exception:
        session.rollback()
        log.exception("Orphan sweep failed; existing jobs may be stuck")
        return 0
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _sweep_orphaned_jobs()
    yield


app = FastAPI(
    title="AeroFly Data Ingestion",
    description="Ingests aerodrome data from DFS (Deutsche Flugsicherung) and other sources.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(aerodromes_router)
app.include_router(charts_router)
app.include_router(usage_router)
app.include_router(extraction_router)
app.include_router(extraction_trigger_router)


@app.get("/health", tags=["health"])
async def health_check():
    """Service health check."""
    return {"status": "ok", "service": "data-ingestion"}
