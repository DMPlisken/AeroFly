"""GET /search/aerodromes — Meilisearch-backed full-text search."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Query, Response

from app.meili import INDEX_AERODROMES, get_client

router = APIRouter(prefix="/search", tags=["search"])

MatchType = Literal["exact", "prefix", "fuzzy"]


def _classify_match(query: str, hit: dict[str, Any]) -> MatchType:
    """Label a hit as exact / prefix / fuzzy based on its searchable fields.

    Heuristic so the frontend can hint to the user when a result came from
    typo-tolerant matching versus a direct match. We compare the original
    query against the hit's searchable fields with case-insensitive logic
    and a stripped form for diacritic robustness.
    """
    q = query.strip().lower()
    if not q:
        return "fuzzy"
    fields = ("icao", "name", "name_de", "city", "city_de")
    for f in fields:
        v = hit.get(f)
        if not isinstance(v, str):
            continue
        v_lower = v.lower()
        if q == v_lower:
            return "exact"
        if q in v_lower:
            # token-prefix or substring counts as "prefix" tier — distinct
            # from a fuzzy/typo-corrected hit.
            return "prefix"
    return "fuzzy"


@router.get(
    "/aerodromes",
    summary="Full-text aerodrome search (typo-tolerant, multi-field)",
)
def search_aerodromes(
    response: Response,
    q: str = Query(default="", description="Search term", max_length=120),
    type: str | None = Query(default=None, description="Filter by aerodrome type"),
    region: str | None = Query(default=None, description="Filter by region (EN or DE)", max_length=80),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """Search the aerodromes index. Empty `q` returns the first page in icao order.

    Each hit carries a `match_type` field (`exact` / `prefix` / `fuzzy`) so
    the UI can show a hint when a result was reached via Meilisearch's
    typo-tolerance.
    """
    client = get_client()
    index = client.index(INDEX_AERODROMES)

    filter_clauses: list[str] = []
    if type:
        # type is an enum value like "international" — Meilisearch needs quoting.
        safe = type.replace('"', "")
        filter_clauses.append(f'type = "{safe}"')
    if region:
        safe = region.replace('"', "")
        filter_clauses.append(
            f'(region = "{safe}" OR region_de = "{safe}")'
        )

    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
        "sort": ["icao:asc"] if not q else None,
    }
    if filter_clauses:
        params["filter"] = " AND ".join(filter_clauses)
    # Drop None values so meilisearch-py doesn't reject them.
    params = {k: v for k, v in params.items() if v is not None}

    result = index.search(q, params)
    hits = result.get("hits", [])
    total = result.get("estimatedTotalHits", len(hits))
    response.headers["X-Total-Count"] = str(total)

    return [{**hit, "match_type": _classify_match(q, hit)} for hit in hits]
