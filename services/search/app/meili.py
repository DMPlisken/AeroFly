"""Meilisearch client + index lifecycle for the aerodromes index.

Single source of truth for index name, schema, synonyms, and ranking config.
Idempotent — `ensure_index()` is safe to call repeatedly on every cold start.
"""

from __future__ import annotations

import logging
from typing import Any

import meilisearch

from app.core.config import settings

logger = logging.getLogger(__name__)

INDEX_AERODROMES = "aerodromes"
PRIMARY_KEY = "icao"

# Fields that can match a query, in priority order.
# `icao_search` is a derived field that pre-expands the ICAO into its useful
# suffixes ("EDDK DDK DK") so Meilisearch's token-prefix matcher can satisfy
# partial-ICAO queries like "DDK" → "EDDK".
SEARCHABLE_ATTRIBUTES = [
    "icao",
    "icao_search",
    "name",
    "name_de",
    "city",
    "city_de",
]

# Fields returned with hits (everything we may want to render).
DISPLAYED_ATTRIBUTES = [
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
]

FILTERABLE_ATTRIBUTES = ["type", "country", "region", "region_de"]
SORTABLE_ATTRIBUTES = ["icao"]

# German umlaut/diacritic ↔ ASCII transliteration. Meilisearch normalizes
# diacritics natively (Köln → kln), but native normalization does NOT cover
# the German "ö → oe" rule pilots actually use. Synonyms close that gap so
# typing "Koeln" still finds "Köln" and vice versa.
SYNONYMS: dict[str, list[str]] = {
    "koeln": ["köln"],
    "köln": ["koeln"],
    "muenchen": ["münchen"],
    "münchen": ["muenchen"],
    "duesseldorf": ["düsseldorf"],
    "düsseldorf": ["duesseldorf"],
    "nuernberg": ["nürnberg"],
    "nürnberg": ["nuernberg"],
    "saarbruecken": ["saarbrücken"],
    "saarbrücken": ["saarbruecken"],
    "tuebingen": ["tübingen"],
    "tübingen": ["tuebingen"],
    "luebeck": ["lübeck"],
    "lübeck": ["luebeck"],
    "ruegen": ["rügen"],
    "rügen": ["ruegen"],
    "wuerzburg": ["würzburg"],
    "würzburg": ["wuerzburg"],
    "guetersloh": ["gütersloh"],
    "gütersloh": ["guetersloh"],
    "zuerich": ["zürich"],
    "zürich": ["zuerich"],
}


_client: meilisearch.Client | None = None


def get_client() -> meilisearch.Client:
    global _client
    if _client is None:
        _client = meilisearch.Client(settings.meili_url, settings.meili_master_key)
    return _client


def ensure_index() -> None:
    """Create the aerodromes index if missing and apply settings.

    Safe to call on every startup — Meilisearch updates settings only when
    they actually change, and `create_index` returns 202 + accepted task even
    if the index already exists (we ignore that branch).
    """
    client = get_client()
    try:
        client.create_index(INDEX_AERODROMES, {"primaryKey": PRIMARY_KEY})
        logger.info("Created Meilisearch index %r", INDEX_AERODROMES)
    except meilisearch.errors.MeilisearchApiError as exc:
        # 4xx with code "index_already_exists" is expected on warm starts.
        if getattr(exc, "code", None) != "index_already_exists":
            raise

    index = client.index(INDEX_AERODROMES)
    index.update_searchable_attributes(SEARCHABLE_ATTRIBUTES)
    index.update_displayed_attributes(DISPLAYED_ATTRIBUTES)
    index.update_filterable_attributes(FILTERABLE_ATTRIBUTES)
    index.update_sortable_attributes(SORTABLE_ATTRIBUTES)
    index.update_synonyms(SYNONYMS)
    # Default typo tolerance only kicks in at 5+ chars for one typo and 9+
    # for two; lowering both lets short city/airport names ("Bonn", "Hahn")
    # tolerate a single typo too ("Boon" → "Bonn").
    index.update_typo_tolerance(
        {
            "enabled": True,
            "minWordSizeForTypos": {"oneTypo": 4, "twoTypos": 8},
        }
    )
    logger.info("Applied Meilisearch settings to %r", INDEX_AERODROMES)


def upsert_documents(docs: list[dict[str, Any]]) -> None:
    """Add or update documents in bulk. Meilisearch handles upsert by primaryKey."""
    if not docs:
        return
    index = get_client().index(INDEX_AERODROMES)
    index.add_documents(docs, primary_key=PRIMARY_KEY)


def delete_document(icao: str) -> None:
    index = get_client().index(INDEX_AERODROMES)
    index.delete_document(icao.upper())
