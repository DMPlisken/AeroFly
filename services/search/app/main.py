"""AeroFly Search — Full-text search over aerodrome data via Meilisearch."""

from fastapi import FastAPI

app = FastAPI(
    title="AeroFly Search",
    description="Search service for aerodrome data — powered by Meilisearch.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/health", tags=["health"])
async def health_check():
    """Service health check."""
    return {"status": "ok", "service": "search"}
