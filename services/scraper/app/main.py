"""AeroFly Scraper — Playwright-based DFS AIP downloader service."""

import logging

from fastapi import FastAPI

from app.api.scrape import router as scrape_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="AeroFly Scraper",
    description=(
        "Headless-Chromium DFS BasicVFR downloader. Owns Playwright + the "
        "Chromium binary; called from data-ingestion when an aerodrome's "
        "charts need refreshing."
    ),
    version="0.1.0",
)

app.include_router(scrape_router)


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "scraper"}
