"""Proxy for extraction-job polling (gateway pass-through to data-ingestion)."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings

router = APIRouter(prefix="/api/extraction", tags=["extraction"])

_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


@router.get("/jobs/{job_id}", summary="Poll an extraction job")
async def get_job(job_id: str, request: Request):
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            upstream = await client.get(
                f"{settings.data_ingestion_url}/extraction/jobs/{job_id}"
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream unreachable: {exc}") from exc
    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)
    return upstream.json()
