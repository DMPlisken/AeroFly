"""Pick candidate chart PNGs for a requested field group.

Reads `manifest.json` written by the scraper (#29). Each document is
tagged with `chart_type` and a `chart_suffix`. We filter candidates by
chart_type acceptable for the field group, then rank within the bucket
using a small structural heuristic — suffix "1" tends to be the VFR
approach chart (VAC) where ARP coords / frequencies are printed; suffix
"4" tends to be the aerodrome chart (ADC) where runway layout lives.

Consumers iterate the ranked list in order (cascade). If consensus
extraction on the first candidate produces no signal, the next one is
tried. This replaces the older Tesseract keyword scorer which was
unreliable because it depended on text density and could not tell a
runway list on an ADC from a mention of "RWY" in a NOTAM.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

log = logging.getLogger(__name__)

FieldGroup = Literal["geo", "runways", "frequencies", "obstacles", "reporting_points"]

# Which chart_types may carry information for a given field group.
# "supplement" (shared AD references) and "other" are never considered.
_ACCEPTED_CHART_TYPES: dict[FieldGroup, tuple[str, ...]] = {
    "geo": ("aerodrome", "terminal"),
    "runways": ("aerodrome",),
    "frequencies": ("aerodrome", "terminal"),
    "obstacles": ("aerodrome",),
    "reporting_points": ("aerodrome",),
}

# Rank hints per field group. Suffixes earlier in the tuple are tried first.
# Anything not listed falls to the end, sorted by suffix.
_SUFFIX_PRIORITY: dict[FieldGroup, tuple[str, ...]] = {
    # VAC tends to carry ARP coords + frequency box + pattern altitudes.
    "geo": ("1", "2", "4"),
    "frequencies": ("1", "2", "4"),
    "reporting_points": ("1", "2"),
    # ADC tends to carry the physical runway layout.
    "runways": ("4", "1", "2"),
    # Obstacles printed on either chart; approach chart usually has more.
    "obstacles": ("1", "2", "4"),
}


@dataclass
class ChartCandidate:
    """One chart selected as a candidate for LLM extraction."""
    path: Path
    chart_type: str
    chart_suffix: str | None
    dfs_name: str


def _load_manifest(aerodrome_dir: Path) -> dict | None:
    manifest_path = aerodrome_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Failed to read %s: %s", manifest_path, exc)
        return None


def _rank_key(doc: dict, priority: tuple[str, ...]) -> tuple[int, str]:
    suffix = (doc.get("chart_suffix") or "").upper()
    try:
        idx = priority.index(suffix)
    except ValueError:
        idx = len(priority)
    return (idx, suffix)


def rank_charts(
    aerodrome_dir: Path,
    *,
    field_group: FieldGroup,
) -> list[ChartCandidate]:
    """Return candidate charts for a field group, best first.

    Empty list if the aerodrome directory lacks a manifest or if no
    document in the manifest matches an accepted chart_type. Missing
    print files are skipped (preview-only documents are ignored because
    the print variant has the full-resolution text we want to send to
    the LLM).
    """
    if not aerodrome_dir.is_dir():
        return []
    manifest = _load_manifest(aerodrome_dir)
    if not manifest:
        return []

    accepted = set(_ACCEPTED_CHART_TYPES.get(field_group, ()))
    priority = _SUFFIX_PRIORITY.get(field_group, ())
    candidates: list[ChartCandidate] = []

    for doc in manifest.get("documents", []):
        if doc.get("chart_type") not in accepted:
            continue
        print_file = doc.get("print_file")
        if not print_file:
            continue
        path = aerodrome_dir / print_file
        if not path.exists():
            continue
        candidates.append(
            ChartCandidate(
                path=path,
                chart_type=doc["chart_type"],
                chart_suffix=doc.get("chart_suffix"),
                dfs_name=doc.get("dfs_name", path.stem),
            )
        )

    candidates.sort(key=lambda c: _rank_key({"chart_suffix": c.chart_suffix}, priority))
    return candidates


def pick_chart(
    aerodrome_dir: Path,
    *,
    field_group: FieldGroup,
) -> ChartCandidate | None:
    """Return the single best candidate, or None. Use `rank_charts` for cascade."""
    ranked = rank_charts(aerodrome_dir, field_group=field_group)
    return ranked[0] if ranked else None
