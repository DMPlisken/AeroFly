"""AeroFly Data Ingestion — DFS data scraping, parsing & import."""

from fastapi import FastAPI

app = FastAPI(
    title="AeroFly Data Ingestion",
    description="Ingests aerodrome data from DFS (Deutsche Flugsicherung) and other sources.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/health", tags=["health"])
async def health_check():
    """Service health check."""
    return {"status": "ok", "service": "data-ingestion"}
