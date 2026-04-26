"""AeroFly Search — Full-text search over aerodrome data via Meilisearch."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.aerodromes import router as aerodromes_router
from app.meili import ensure_index
from app.sync import bulk_load, subscribe_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ensure index + bulk-load + spawn Redis subscriber.

    Bulk-load failure is logged but non-fatal — the service can still answer
    queries from whatever's already in Meilisearch (or return empty), and the
    subscriber will catch up on the next published event.
    """
    stop_event = asyncio.Event()
    subscriber_task: asyncio.Task | None = None

    try:
        ensure_index()
    except Exception:
        logger.exception("Failed to ensure Meilisearch index on startup")

    try:
        await bulk_load()
    except Exception:
        logger.exception("Initial bulk load failed; service will still start")

    subscriber_task = asyncio.create_task(subscribe_loop(stop_event), name="aerodrome-subscriber")

    try:
        yield
    finally:
        stop_event.set()
        if subscriber_task is not None:
            subscriber_task.cancel()
            try:
                await subscriber_task
            except (asyncio.CancelledError, Exception):
                pass


app = FastAPI(
    title="AeroFly Search",
    description="Search service for aerodrome data — powered by Meilisearch.",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.include_router(aerodromes_router)


@app.get("/health", tags=["health"])
async def health_check():
    """Service health check."""
    return {"status": "ok", "service": "search"}
