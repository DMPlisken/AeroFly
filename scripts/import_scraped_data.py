"""Import scraped DFS aerodrome data into the ingest schema.

Reads every `data/aerodromes/*/manifest.json` produced by the DFS Playwright
scraper (feat/1) and inserts:

- One `aerodromes` row per folder (ICAO + name + AIRAC cycle)
- One `charts` row per document in the manifest

Structured fields such as runways, frequencies, coordinates, elevation are
NOT in the manifest — they require the HTML/chart parser (follow-up work).

Idempotent: uses ON CONFLICT DO NOTHING semantics for aerodromes and the
existing `ix_charts_source_url` unique index for charts. Re-running only adds
new rows.

Use --wipe to drop all existing aerodromes first (cascades to runways,
frequencies, charts, notams).

Usage:

    # From repo root, against host-mapped postgres:
    DATABASE_URL=postgresql://aerofly:changeme@localhost:15432/aerofly \
        python scripts/import_scraped_data.py

    # Inside data-ingestion container (data/ mounted read-only):
    docker compose exec data-ingestion python scripts/import_scraped_data.py

    # Wipe first:
    docker compose exec data-ingestion python scripts/import_scraped_data.py --wipe
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
_IN_CONTAINER = Path("/app/shared").exists() and not (
    _PROJECT_ROOT / "shared" / "python"
).exists()

if _IN_CONTAINER:
    sys.path.insert(0, "/app")
    _DATA_ROOT = Path("/app/data/aerodromes")
else:
    sys.path.insert(0, str(_PROJECT_ROOT))
    sys.path.insert(0, str(_PROJECT_ROOT / "services" / "data-ingestion"))
    import shared.python as _shared_pkg  # type: ignore  # noqa: E402
    import shared.python.models as _shared_models  # type: ignore  # noqa: E402
    import shared.python.models.base as _shared_models_base  # type: ignore  # noqa: E402
    import shared.python.schemas as _shared_schemas  # type: ignore  # noqa: E402
    import shared.python.schemas.enums as _shared_schemas_enums  # type: ignore  # noqa: E402

    sys.modules.setdefault("shared", _shared_pkg)
    sys.modules.setdefault("shared.schemas", _shared_schemas)
    sys.modules.setdefault("shared.schemas.enums", _shared_schemas_enums)
    sys.modules.setdefault("shared.models", _shared_models)
    sys.modules.setdefault("shared.models.base", _shared_models_base)
    _DATA_ROOT = _PROJECT_ROOT / "data" / "aerodromes"

from sqlalchemy import text as sql_text  # noqa: E402

from app.db import get_session_factory  # noqa: E402
from app.db.models import Aerodrome, AiracCycle, Chart  # noqa: E402
from shared.schemas.enums import AerodromeType, ChartType  # noqa: E402


# DFS AIP public URL builder. The permalinks in manifests are relative to:
#   https://aip.dfs.de/BasicVFR/{edition}/
_DFS_BASE = "https://aip.dfs.de/BasicVFR"


def database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = os.getenv("POSTGRES_USER", "aerofly")
    password = os.getenv("POSTGRES_PASSWORD", "changeme")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "aerofly")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def edition_to_airac(edition: str) -> str:
    """Convert scraper edition string like '2026APR02' -> AIRAC cycle '2026-04'."""
    match = re.match(r"(\d{4})([A-Z]{3})(\d{2})", edition)
    if not match:
        return "unknown"
    year, month_abbr, _ = match.groups()
    month_map = {
        "JAN": "01",
        "FEB": "02",
        "MAR": "03",
        "APR": "04",
        "MAY": "05",
        "JUN": "06",
        "JUL": "07",
        "AUG": "08",
        "SEP": "09",
        "OCT": "10",
        "NOV": "11",
        "DEC": "12",
    }
    return f"{year}-{month_map.get(month_abbr, '01')}"


def classify_chart(dfs_name: str) -> ChartType:
    """Best-effort chart type from the DFS document name."""
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="TRUNCATE aerodromes (and children via CASCADE) before importing",
    )
    args = parser.parse_args()

    if not _DATA_ROOT.exists():
        print(
            f"FAIL data directory  : {_DATA_ROOT} does not exist.\n"
            "     Inside the container? make sure ./data is mounted to /app/data.",
            file=sys.stderr,
        )
        return 1

    manifests = sorted(_DATA_ROOT.glob("*/manifest.json"))
    if not manifests:
        print(f"FAIL no manifests    : no */manifest.json under {_DATA_ROOT}", file=sys.stderr)
        return 1

    print(f"OK  manifests found    : {len(manifests)}")

    Session = get_session_factory(database_url())
    session = Session()
    try:
        if args.wipe:
            session.execute(sql_text("TRUNCATE TABLE ingest.aerodromes CASCADE"))
            print("OK  wiped aerodromes   : TRUNCATE CASCADE")

        # Track AIRAC cycles we encounter so we can add the rows once.
        seen_cycles: set[str] = set()

        added_aerodromes = 0
        skipped_aerodromes = 0
        added_charts = 0
        skipped_charts = 0

        for manifest_path in manifests:
            with manifest_path.open(encoding="utf-8") as fh:
                manifest = json.load(fh)

            icao = manifest["icao"].strip().upper()
            if len(icao) != 4 or not icao.isalpha():
                print(f"SKIP invalid icao    : {icao}", file=sys.stderr)
                continue

            airac = edition_to_airac(manifest.get("edition", ""))

            # Ensure AIRAC cycle exists
            if airac not in seen_cycles and airac != "unknown":
                if session.get(AiracCycle, airac) is None:
                    # Effective dates are unknown from the scraper edition string;
                    # use the first of that month as a placeholder.
                    year, month = airac.split("-")
                    effective_from = date(int(year), int(month), 1)
                    effective_to = (
                        date(int(year), int(month) + 1, 1)
                        if int(month) < 12
                        else date(int(year) + 1, 1, 1)
                    )
                    session.add(
                        AiracCycle(
                            ident=airac,
                            effective_from=effective_from,
                            effective_to=effective_to,
                            is_current=True,
                        )
                    )
                seen_cycles.add(airac)

            # Aerodrome
            entity = session.get(Aerodrome, icao)
            if entity is None:
                name = manifest.get("name") or icao
                entity = Aerodrome(
                    icao=icao,
                    name=name,
                    name_de=name,  # manifest has only one name; parser will refine later
                    country="DE",
                    type=AerodromeType.OTHER,
                    source_airac_cycle=airac if airac != "unknown" else None,
                )
                session.add(entity)
                session.flush()
                added_aerodromes += 1
            else:
                skipped_aerodromes += 1

            # Charts
            for doc in manifest.get("documents", []):
                if doc.get("error"):
                    continue

                permalink = doc.get("permalink") or ""
                edition = manifest.get("edition", "")
                source_url = (
                    f"{_DFS_BASE}/{edition}/{permalink}"
                    if edition and permalink
                    else f"local://{icao}/{doc.get('normalized_name', 'unknown')}"
                )

                exists = (
                    session.query(Chart)
                    .filter(Chart.source_url == source_url)
                    .first()
                )
                if exists is not None:
                    skipped_charts += 1
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
                added_charts += 1

        session.commit()
        total_aerodromes = session.query(Aerodrome).count()
        total_charts = session.query(Chart).count()

        print(f"OK  aerodromes added   : {added_aerodromes}")
        print(f"OK  aerodromes skipped : {skipped_aerodromes} (already existed)")
        print(f"OK  charts added       : {added_charts}")
        print(f"OK  charts skipped     : {skipped_charts} (same source_url)")
        print(f"OK  total aerodromes   : {total_aerodromes}")
        print(f"OK  total charts       : {total_charts}")
        return 0
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        print(f"FAIL import          : {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
