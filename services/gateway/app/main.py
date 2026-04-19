"""AeroFly Gateway — API Gateway, Auth & Routing."""

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.aerodromes import router as aerodromes_router
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
    expose_headers=["X-Total-Count", "X-Request-ID"],
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject an X-Request-ID header on every response for trace correlation."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)

app.include_router(aerodromes_router)


@app.get("/api/health", tags=["health"])
async def health_check():
    """Service health check."""
    return {"status": "ok", "service": "gateway"}
