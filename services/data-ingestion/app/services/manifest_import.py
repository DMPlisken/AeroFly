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

    Returns a small summary dict (`{"aerodromes_added": int, "charts_added": int,
    "charts_skipped": int, "edition": str, "airac": str}`). Idempotent: aerodromes
    and charts that already exist are left alone.
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
        "charts_skipped": 0,
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

    for doc in manifest.get("documents", []):
        if doc.get("error"):
            continue

        permalink = doc.get("permalink") or ""
        source_url = (
            f"{_DFS_BASE}/{edition}/{permalink}"
            if edition and permalink
            else f"local://{icao}/{doc.get('normalized_name', 'unknown')}"
        )

        existing = (
            session.query(Chart).filter(Chart.source_url == source_url).first()
        )
        if existing is not None:
            summary["charts_skipped"] += 1
            continue

        dfs_name = doc.get("dfs_name") or doc.get("normalized_name") or "Chart"
        local_preview = doc.get("preview_file")
        local_path = (
            f"/app/data/aerodromes/{icao}/{local_preview}" if local_preview else None
        )

        session.add(
            Chart(
                aerodrome_icao=icao,
                chart_type=classify_chart(dfs_name),
                title=dfs_name,
                title_de=dfs_name,
                source_url=source_url,
                local_path=local_path,
                language="de",
                source_airac_cycle=airac if airac != "unknown" else None,
            )
        )
        summary["charts_added"] += 1

    # Refresh the aerodrome's source_airac_cycle so the detail header
    # reflects the freshly-scraped edition even when no new charts landed.
    if airac != "unknown" and aerodrome.source_airac_cycle != airac:
        aerodrome.source_airac_cycle = airac

    return summary
