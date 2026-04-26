"""Gateway proxy for the search service."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query, Response

from app.core.config import settings

router = APIRouter(prefix="/api/search", tags=["search"])

_REQUEST_TIMEOUT = httpx.Timeout(5.0, connect=2.0)


@router.get(
    "/aerodromes",
    summary="Full-text aerodrome search (typo-tolerant)",
)
async def search_aerodromes(
    response: Response,
    q: str = Query(default="", description="Search term", max_length=120),
    type: str | None = Query(default=None, description="Filter by aerodrome type"),
    region: str | None = Query(default=None, description="Filter by region (EN or DE)", max_length=80),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    params: dict[str, str | int] = {"limit": limit, "offset": offset}
    if q:
        params["q"] = q
    if type:
        params["type"] = type
    if region:
        params["region"] = region

    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        try:
            upstream = await client.get(
                f"{settings.search_url}/search/aerodromes",
                params=params,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Search upstream unreachable: {exc}") from exc

    if total := upstream.headers.get("x-total-count"):
        response.headers["X-Total-Count"] = total
    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)
    return upstream.json()
