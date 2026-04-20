"""Proxy for LLM API usage endpoints exposed by data-ingestion."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from app.core.config import settings

router = APIRouter(prefix="/api/usage", tags=["usage"])

_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


@router.get("/summary")
async def usage_summary(request: Request):
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            upstream = await client.get(f"{settings.data_ingestion_url}/usage/summary")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"upstream unreachable: {exc}") from exc
    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)
    return upstream.json()


@router.get("/recent")
async def usage_recent(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
):
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            upstream = await client.get(
                f"{settings.data_ingestion_url}/usage/recent",
                params={"limit": limit},
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"upstream unreachable: {exc}") from exc
    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)
    return upstream.json()
