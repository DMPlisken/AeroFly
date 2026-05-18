"""Pure-function chart name classifiers.

Copied 1:1 from `scripts/scrape_dfs_aip.py` so the scraper service is
self-contained. The CLI script keeps its own copy for backward
compatibility. If these ever diverge, the source of truth lives here
(both services consume scraped output, the CLI is just a manual fallback).
"""

from __future__ import annotations

import re

_ICAO_RE = re.compile(r"\bED[A-Z]{2}\b")
_AD_SUPPLEMENT_RE = re.compile(r"^\s*AD\s+\d", re.IGNORECASE)
_TRAILING_SUFFIX_RE = re.compile(r"([A-Z0-9]+)\s*$")


def classify_chart_type(dfs_name: str) -> str:
    """Classify a DFS document name into a coarse chart type."""
    name = dfs_name.strip()
    upper = name.upper()
    if _AD_SUPPLEMENT_RE.match(upper) and not _ICAO_RE.search(upper):
        return "supplement"
    if "TERMINAL CHART" in upper:
        return "terminal"
    if re.match(r"^ED[A-Z]{2}\b", upper):
        return "aerodrome"
    return "other"


def extract_chart_suffix(dfs_name: str) -> str | None:
    """Return the trailing identifier after the airport portion (e.g. '1', '2A')."""
    upper = dfs_name.strip().upper()
    if not re.match(r"^ED[A-Z]{2}\b", upper):
        return None
    match = _TRAILING_SUFFIX_RE.search(upper)
    if match:
        token = match.group(1)
        if _ICAO_RE.fullmatch(token):
            return None
        return token
    return None


def normalize_filename(dfs_name: str) -> str:
    """Make a DFS doc name usable as a filename: spaces → underscores."""
    normalized = re.sub(r"\s+", "_", dfs_name.strip())
    normalized = re.sub(r"[^\w\-.]", "_", normalized)
    return normalized


def extract_icao(text: str) -> str | None:
    """Pull a 4-letter ICAO (ED**) out of free text."""
    match = re.search(r"\b(ED[A-Z]{2})\b", text)
    return match.group(1) if match else None
