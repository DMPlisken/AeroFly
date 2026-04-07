"""AeroFly Gateway — API Gateway, Auth & Routing."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title="AeroFly API",
    description=(
        "Aerodrome information compendium for German airports. "
        "Index, search and serve DFS (Deutsche Flugsicherung) data."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["health"])
async def health_check():
    """Service health check."""
    return {"status": "ok", "service": "gateway"}
