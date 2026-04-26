"""Outbound Redis pub/sub events.

Per CLAUDE.md the data-ingestion service is the source of truth for aerodrome
data; downstream services (currently: search) subscribe to these channels to
keep their own indexes/projections in sync. Channel names are kept in sync
with the search service's `app/sync.py` constants.
"""

from __future__ import annotations

import json
import logging

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

CHANNEL_AERODROME_UPSERT = "aerodrome.upsert"
CHANNEL_AERODROME_DELETE = "aerodrome.delete"

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def publish_aerodrome_upsert(icao: str) -> None:
    """Notify subscribers that aerodrome `icao` was created or modified.

    Best-effort — failures are logged but never propagated; data integrity
    is in Postgres. The search service's startup bulk-load is the safety
    net for any missed events.
    """
    payload = json.dumps({"icao": icao.upper()})
    try:
        _get_client().publish(CHANNEL_AERODROME_UPSERT, payload)
    except Exception:
        logger.exception("Failed to publish %s for %s", CHANNEL_AERODROME_UPSERT, icao)


def publish_aerodrome_delete(icao: str) -> None:
    payload = json.dumps({"icao": icao.upper()})
    try:
        _get_client().publish(CHANNEL_AERODROME_DELETE, payload)
    except Exception:
        logger.exception("Failed to publish %s for %s", CHANNEL_AERODROME_DELETE, icao)
