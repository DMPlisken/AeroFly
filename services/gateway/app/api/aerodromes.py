"""Aerodrome API — proxies to data-ingestion.

Gateway never touches the domain database. It calls the owner service via HTTP
and adds the API-gateway concerns (CORS, request-id, consistent errors). When
the Search service gets Meilisearch + projections, the upstream becomes search.
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.core.config import settings

router = APIRouter(prefix="/api/aerodromes", tags=["aerodromes"])

_REQUEST_TIMEOUT = httpx.Timeout(10.0, connect=3.0)


@router.get("", summary="List aerodromes")
async def list_aerodromes(
    request: Request,
    response: Response,
    q: str | None = Query(default=None, description="Prefix match against ICAO / name / name_de", max_length=120),
    type: str | None = Query(default=None, description="Filter by aerodrome type"),
    region: str | None = Query(default=None, description="Filter by region (EN or DE)", max_length=80),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Return a paginated list of aerodromes, with `X-Total-Count` header passed through."""
    params = {"limit": limit, "offset": offset}
    if q:
        params["q"] = q
    if type:
        params["type"] = type
    if region:
        params["region"] = region

    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        try:
            upstream = await client.get(
                f"{settings.data_ingestion_url}/aerodromes",
                params=params,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream unreachable: {exc}") from exc

    if total := upstream.headers.get("x-total-count"):
        response.headers["X-Total-Count"] = total
    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)
    return upstream.json()


@router.get("/{icao}", summary="Aerodrome detail")
async def get_aerodrome(icao: str, request: Request):
    """Return one aerodrome with runways, frequencies, charts, and NOTAMs."""
    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        try:
            upstream = await client.get(
                f"{settings.data_ingestion_url}/aerodromes/{icao}",
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream unreachable: {exc}") from exc

    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)
    return upstream.json()


@router.post(
    "/{icao}/extract",
    status_code=202,
    summary="Trigger async per-aerodrome LLM extraction (legacy — re-extracts existing charts only)",
)
async def trigger_extraction(icao: str, request: Request):
    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        try:
            upstream = await client.post(
                f"{settings.data_ingestion_url}/aerodromes/{icao}/extract"
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream unreachable: {exc}") from exc

    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)
    return upstream.json()


@router.post(
    "/{icao}/sync",
    status_code=202,
    summary="Refresh DFS charts then re-extract structured fields (full sync)",
)
async def trigger_sync(icao: str, request: Request):
    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        try:
            upstream = await client.post(
                f"{settings.data_ingestion_url}/aerodromes/{icao}/sync"
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream unreachable: {exc}") from exc

    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)
    return upstream.json()


@router.get(
    "/{icao}/extraction/latest",
    summary="Latest extraction job for an aerodrome",
)
async def latest_extraction(icao: str, request: Request):
    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        try:
            upstream = await client.get(
                f"{settings.data_ingestion_url}/extraction/aerodromes/{icao}/latest"
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream unreachable: {exc}") from exc

    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)
    return upstream.json()


@router.patch(
    "/{icao}/charts/{chart_id}/rotation",
    summary="Persist user's preferred rotation (0/90/180/270) for a chart",
)
async def update_chart_rotation(icao: str, chart_id: int, request: Request):
    body = await request.body()
    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        try:
            upstream = await client.patch(
                f"{settings.data_ingestion_url}/aerodromes/{icao}/charts/{chart_id}/rotation",
                content=body,
                headers={"content-type": request.headers.get("content-type", "application/json")},
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream unreachable: {exc}") from exc

    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)
    return upstream.json()
