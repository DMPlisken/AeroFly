"""AIRAC edition auto-discovery.

The DFS BasicVFR site is published per AIRAC cycle (~28 days). Each cycle
has its own URL prefix like `2026MAY15`. The scraper's job runs against
ONE specific edition — when triggered without an explicit edition argument
we want to discover the current one automatically.

DFS publishes the edition list at `/BasicVFR/` (root) where the active
edition is linked at the top. We fetch that page once, parse the latest
edition slug, and cache it briefly so multiple incoming scrape requests
don't hammer DFS.
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass

import httpx

from app.core.config import settings

# Edition slug looks like 2026APR02, 2026MAY15. YYYY + MON3 + DD.
_EDITION_RE = re.compile(r"\b(20\d{2}[A-Z]{3}\d{2})\b")


@dataclass
class _Cache:
    edition: str
    fetched_at: float


_cache: _Cache | None = None
_lock = asyncio.Lock()


async def discover_current_edition(force_refresh: bool = False) -> str:
    """Return the AIRAC edition slug currently active on the DFS site.

    Cached for `airac_cache_ttl_seconds` so consecutive scrape requests
    inside the same AIRAC cycle don't re-hit DFS. Returns a slug like
    "2026MAY15".
    """
    global _cache
    async with _lock:
        if not force_refresh and _cache is not None:
            age = time.time() - _cache.fetched_at
            if age < settings.airac_cache_ttl_seconds:
                return _cache.edition

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(f"{settings.dfs_base_url}/BasicVFR/")
            response.raise_for_status()

        # DFS redirects /BasicVFR/ → /BasicVFR/<slug>/chapter/<hash>.html.
        # The slug lives in the final URL path; the response body never
        # mentions it. Search the URL first, fall back to body.
        match = _EDITION_RE.search(str(response.url)) or _EDITION_RE.search(response.text)
        if match is None:
            raise RuntimeError(
                "Could not discover current AIRAC edition. Final URL was "
                f"{response.url}; expected a slug like 'YYYYMONDD' "
                "somewhere in the redirect chain. DFS site layout may have changed."
            )
        _cache = _Cache(edition=match.group(1), fetched_at=time.time())
        return _cache.edition
