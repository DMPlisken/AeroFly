"""Sync the Meilisearch aerodromes index with data-ingestion.

Two flows:
1. Bulk load on startup — fetch the full list from data-ingestion's HTTP API
   and re-index. Per CLAUDE.md ("Database per module") the search service
   never reads `ingest.aerodromes` directly; it only consumes the data via
   the data-ingestion service.
2. Delta updates — Redis pub/sub subscriber that re-indexes a single
   aerodrome when data-ingestion publishes `aerodrome.upsert {icao}`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
import redis.asyncio as aioredis

from app.core.config import settings
from app.meili import delete_document, upsert_documents

logger = logging.getLogger(__name__)

CHANNEL_AERODROME_UPSERT = "aerodrome.upsert"
CHANNEL_AERODROME_DELETE = "aerodrome.delete"

# Fields we project from data-ingestion's aerodrome JSON into the Meilisearch
# document. Anything outside this list is dropped to keep the index lean.
_INDEXED_FIELDS = {
    "icao",
    "iata",
    "name",
    "name_de",
    "city",
    "city_de",
    "region",
    "region_de",
    "country",
    "type",
    "latitude",
    "longitude",
    "elevation_ft",
}


def _icao_search_field(icao: str | None) -> str:
    """Pre-expand the ICAO into matchable suffixes for the Meilisearch index.

    Meilisearch's token-prefix matcher won't satisfy `q="DDK"` on `icao="EDDK"`
    on its own (DDK is not a prefix of EDDK). Listing the trailing 3- and
    2-char suffixes alongside the full ICAO turns it into a prefix match.
    """
    if not isinstance(icao, str) or len(icao) < 2:
        return icao or ""
    parts = [icao]
    for n in (3, 2):
        if len(icao) > n:
            parts.append(icao[-n:])
    return " ".join(parts)


def _project(aerodrome: dict[str, Any]) -> dict[str, Any]:
    """Project a data-ingestion aerodrome record onto the Meilisearch schema."""
    doc = {k: aerodrome.get(k) for k in _INDEXED_FIELDS if k in aerodrome}
    doc["icao_search"] = _icao_search_field(aerodrome.get("icao"))
    return doc


async def bulk_load() -> int:
    """Fetch every aerodrome from data-ingestion and re-index. Returns count."""
    url = f"{settings.data_ingestion_url}/aerodromes"
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0)) as client:
        # 433 fits in one page; the limit cap is 200 per call so we paginate.
        items: list[dict[str, Any]] = []
        offset = 0
        page = 200
        while True:
            resp = await client.get(url, params={"limit": page, "offset": offset})
            resp.raise_for_status()
            chunk = resp.json()
            if not chunk:
                break
            items.extend(chunk)
            if len(chunk) < page:
                break
            offset += page

    docs = [_project(a) for a in items]
    upsert_documents(docs)
    logger.info("Bulk-loaded %d aerodromes into Meilisearch", len(docs))
    return len(docs)


async def reindex_one(icao: str) -> None:
    """Fetch a single aerodrome and upsert it into Meilisearch."""
    url = f"{settings.data_ingestion_url}/aerodromes/{icao.upper()}"
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
        resp = await client.get(url)
        if resp.status_code == 404:
            delete_document(icao)
            logger.info("Removed %s from index (404 from data-ingestion)", icao)
            return
        resp.raise_for_status()
        aerodrome = resp.json()
    upsert_documents([_project(aerodrome)])
    logger.info("Re-indexed %s", icao.upper())


async def _handle_message(channel: str, payload: str) -> None:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        logger.warning("Ignoring non-JSON message on %s: %r", channel, payload)
        return
    icao = data.get("icao")
    if not isinstance(icao, str) or len(icao) != 4:
        logger.warning("Ignoring message without valid icao on %s: %r", channel, data)
        return
    try:
        if channel == CHANNEL_AERODROME_DELETE:
            delete_document(icao)
        else:
            await reindex_one(icao)
    except Exception:
        logger.exception("Failed to process %s message for %s", channel, icao)


async def subscribe_loop(stop_event: asyncio.Event) -> None:
    """Long-running task: subscribe to aerodrome.* channels and react.

    Reconnects on connection drop. Exits cleanly when `stop_event` is set.
    """
    backoff = 1.0
    while not stop_event.is_set():
        try:
            client = aioredis.from_url(settings.redis_url, decode_responses=True)
            pubsub = client.pubsub()
            await pubsub.subscribe(CHANNEL_AERODROME_UPSERT, CHANNEL_AERODROME_DELETE)
            logger.info(
                "Subscribed to Redis channels: %s, %s",
                CHANNEL_AERODROME_UPSERT,
                CHANNEL_AERODROME_DELETE,
            )
            backoff = 1.0
            async for msg in pubsub.listen():
                if stop_event.is_set():
                    break
                if msg.get("type") != "message":
                    continue
                channel = msg.get("channel")
                payload = msg.get("data")
                if isinstance(channel, str) and isinstance(payload, str):
                    await _handle_message(channel, payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Redis subscriber crashed; retrying in %.1fs", backoff)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, 30.0)
        finally:
            try:
                await pubsub.unsubscribe()
                await pubsub.aclose()
                await client.aclose()
            except Exception:
                pass
