"""Per-aerodrome manifest import.

Extracted from `scripts/import_scraped_data.py` so the sync pipeline can
import ONE aerodrome's freshly scraped manifest at a time. The bulk
script still works unchanged for host-side ops.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Aerodrome, AiracCycle, Chart
from shared.schemas.enums import AerodromeType, ChartType

log = logging.getLogger(__name__)

DATA_ROOT = Path("/app/data/aerodromes")
_DFS_BASE = "https://aip.dfs.de/BasicVFR"

_MONTH_MAP = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
    "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
    "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}


def edition_to_airac(edition: str) -> str:
    """Convert a scraper edition slug like '2026MAY05' → AIRAC cycle '2026-05'."""
    match = re.match(r"(\d{4})([A-Z]{3})(\d{2})", edition)
    if not match:
        return "unknown"
    year, month_abbr, _ = match.groups()
    return f"{year}-{_MONTH_MAP.get(month_abbr, '01')}"


def classify_chart(dfs_name: str) -> ChartType:
    name = dfs_name.lower()
    if re.search(r"\bad[\s_]*2[-_]", name):
        return ChartType.AD_INFO
    if "terminal" in name:
        return ChartType.AD_CHART
    if "parking" in name or "apron" in name:
        return ChartType.PARKING
    if "taxi" in name:
        return ChartType.TAXI
    if "sid" in name:
        return ChartType.SID
    if "star" in name:
        return ChartType.STAR
    if "iac" in name or "ils" in name or "approach" in name:
        return ChartType.IAC
    if "vac" in name or "visual" in name:
        return ChartType.VAC
    return ChartType.GENERAL


def _ensure_airac_cycle(session: Session, airac: str) -> None:
    if airac == "unknown":
        return
    if session.get(AiracCycle, airac) is not None:
        return
    year, month = airac.split("-")
    effective_from = date(int(year), int(month), 1)
    if int(month) < 12:
        effective_to = date(int(year), int(month) + 1, 1)
    else:
        effective_to = date(int(year) + 1, 1, 1)
    session.add(
        AiracCycle(
            ident=airac,
            effective_from=effective_from,
            effective_to=effective_to,
            is_current=True,
        )
    )


def import_one_manifest(
    icao: str,
    session: Session,
    *,
    data_root: Path = DATA_ROOT,
) -> dict[str, Any]:
    """Import a single aerodrome's `manifest.json` into the DB.

    Idempotent semantics (BUG-013):

    - Charts are matched by `(aerodrome_icao, title)`, NOT by `source_url`.
      The `source_url` contains the AIRAC edition slug and therefore
      changes every cycle — matching on it would create a parallel row
      set instead of refreshing the existing one.
    - On match: the row is updated in place (new `source_url`,
      `local_path`, `source_airac_cycle`, `title_de`, classification),
      preserving user-editable fields like `rotation_degrees`.
    - Charts present in the DB but absent from the new manifest are
      deleted — DFS dropped them, so should we.

    Returns a summary dict with counts.
    """
    icao = icao.strip().upper()
    manifest_path = data_root / icao / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest for {icao} at {manifest_path}")

    with manifest_path.open(encoding="utf-8") as fh:
        manifest = json.load(fh)

    if manifest.get("icao", "").upper() != icao:
        raise ValueError(
            f"Manifest icao={manifest.get('icao')!r} does not match requested {icao!r}"
        )

    edition = manifest.get("edition", "")
    airac = edition_to_airac(edition)
    _ensure_airac_cycle(session, airac)

    summary = {
        "aerodromes_added": 0,
        "charts_added": 0,
        "charts_updated": 0,
        "charts_deleted": 0,
        "edition": edition,
        "airac": airac,
    }

    aerodrome = session.get(Aerodrome, icao)
    if aerodrome is None:
        name = manifest.get("name") or icao
        aerodrome = Aerodrome(
            icao=icao,
            name=name,
            name_de=name,
            country="DE",
            type=AerodromeType.OTHER,
            source_airac_cycle=airac if airac != "unknown" else None,
        )
        session.add(aerodrome)
        session.flush()
        summary["aerodromes_added"] = 1

    # Build a lookup of existing charts for this icao keyed by title so we
    # can detect "still present", "newly added", "removed".
    existing_by_title: dict[str, Chart] = {
        c.title: c
        for c in session.query(Chart).filter(Chart.aerodrome_icao == icao).all()
    }
    seen_titles: set[str] = set()

    for doc in manifest.get("documents", []):
        if doc.get("error"):
            continue

        dfs_name = doc.get("dfs_name") or doc.get("normalized_name") or "Chart"
        seen_titles.add(dfs_name)

        permalink = doc.get("permalink") or ""
        source_url = (
            f"{_DFS_BASE}/{edition}/{permalink}"
            if edition and permalink
            else f"local://{icao}/{doc.get('normalized_name', 'unknown')}"
        )
        local_preview = doc.get("preview_file")
        local_path = (
            f"/app/data/aerodromes/{icao}/{local_preview}" if local_preview else None
        )
        chart_type = classify_chart(dfs_name)

        existing = existing_by_title.get(dfs_name)
        if existing is not None:
            # In-place update — DO NOT touch rotation_degrees (user-edited).
            existing.chart_type = chart_type
            existing.title_de = dfs_name
            existing.source_url = source_url
            existing.local_path = local_path
            existing.language = "de"
            if airac != "unknown":
                existing.source_airac_cycle = airac
            summary["charts_updated"] += 1
            continue

        session.add(
            Chart(
                aerodrome_icao=icao,
                chart_type=chart_type,
                title=dfs_name,
                title_de=dfs_name,
                source_url=source_url,
                local_path=local_path,
                language="de",
                source_airac_cycle=airac if airac != "unknown" else None,
            )
        )
        summary["charts_added"] += 1

    # Anything left in the existing set but not in the manifest is gone
    # from DFS — drop it.
    for title, chart in existing_by_title.items():
        if title not in seen_titles:
            session.delete(chart)
            summary["charts_deleted"] += 1

    if airac != "unknown" and aerodrome.source_airac_cycle != airac:
        aerodrome.source_airac_cycle = airac

    return summary
