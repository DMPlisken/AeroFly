"""Seed the ingest schema with 10 real major German airports.

Idempotent: re-running does not duplicate rows. Data is drawn from
publicly known airport information (Wikipedia / published AIP extracts).
Frequencies may drift slightly from the current AIRAC cycle — the DFS
scraper (issue #1) replaces these values once it lands.

Run from the project root:

    DATABASE_URL=postgresql://aerofly:changeme@localhost:15432/aerofly \
        python scripts/seed_demo_data.py

Or inside the container:

    docker compose exec data-ingestion python scripts/seed_demo_data.py
"""

from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
_IN_CONTAINER = Path("/app/shared").exists() and not (
    _PROJECT_ROOT / "shared" / "python"
).exists()

if _IN_CONTAINER:
    sys.path.insert(0, "/app")
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

from app.db import get_session_factory  # noqa: E402
from app.db.models import Aerodrome, AiracCycle, Frequency, Runway  # noqa: E402
from shared.schemas.enums import (  # noqa: E402
    AerodromeType,
    FrequencyType,
    RunwaySurface,
)


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


CYCLE = "2026-04"

# 10 major German aerodromes. Each tuple:
#   (icao, iata, name_en, name_de, city, region, type, lat, lon, elev_ft,
#    runways=[(le, he, length_m, width_m, ils_le, ils_he)],
#    freqs=[(type, callsign_de, mhz)])
AERODROMES: list[dict] = [
    {
        "icao": "EDDF", "iata": "FRA",
        "name": "Frankfurt Airport", "name_de": "Flughafen Frankfurt am Main",
        "city": "Frankfurt", "city_de": "Frankfurt am Main",
        "region": "Hesse", "region_de": "Hessen",
        "type": AerodromeType.INTERNATIONAL,
        "lat": 50.033333, "lon": 8.570556, "elev_ft": 364,
        "runways": [
            ("07C", "25C", 4000, 60, True, True),
            ("07R", "25L", 4000, 45, True, True),
            ("07L", "25R", 2800, 45, True, False),
            ("18", "36", 4000, 45, False, False),
        ],
        "freqs": [
            (FrequencyType.TWR, "Langen Tower", Decimal("119.900")),
            (FrequencyType.GND, "Apron Frankfurt", Decimal("121.800")),
            (FrequencyType.ATIS, "Frankfurt ATIS", Decimal("118.025")),
            (FrequencyType.DEL, "Langen Delivery", Decimal("121.900")),
        ],
    },
    {
        "icao": "EDDM", "iata": "MUC",
        "name": "Munich Airport", "name_de": "Flughafen München",
        "city": "Munich", "city_de": "München",
        "region": "Bavaria", "region_de": "Bayern",
        "type": AerodromeType.INTERNATIONAL,
        "lat": 48.353889, "lon": 11.786111, "elev_ft": 1487,
        "runways": [
            ("08L", "26R", 4000, 60, True, True),
            ("08R", "26L", 4000, 60, True, True),
        ],
        "freqs": [
            (FrequencyType.TWR, "München Turm", Decimal("118.700")),
            (FrequencyType.GND, "Apron München Nord", Decimal("121.700")),
            (FrequencyType.ATIS, "München ATIS", Decimal("123.125")),
            (FrequencyType.DEL, "München Delivery", Decimal("121.825")),
        ],
    },
    {
        "icao": "EDDH", "iata": "HAM",
        "name": "Hamburg Airport", "name_de": "Hamburg Airport Helmut Schmidt",
        "city": "Hamburg", "city_de": "Hamburg",
        "region": "Hamburg", "region_de": "Hamburg",
        "type": AerodromeType.INTERNATIONAL,
        "lat": 53.630278, "lon": 9.988333, "elev_ft": 53,
        "runways": [
            ("05", "23", 3250, 46, True, True),
            ("15", "33", 3666, 46, True, True),
        ],
        "freqs": [
            (FrequencyType.TWR, "Hamburg Turm", Decimal("126.900")),
            (FrequencyType.GND, "Hamburg Rollkontrolle", Decimal("121.850")),
            (FrequencyType.ATIS, "Hamburg ATIS", Decimal("126.700")),
        ],
    },
    {
        "icao": "EDDB", "iata": "BER",
        "name": "Berlin Brandenburg Airport", "name_de": "Flughafen Berlin Brandenburg Willy Brandt",
        "city": "Berlin", "city_de": "Berlin",
        "region": "Brandenburg", "region_de": "Brandenburg",
        "type": AerodromeType.INTERNATIONAL,
        "lat": 52.362222, "lon": 13.500556, "elev_ft": 157,
        "runways": [
            ("07L", "25R", 3600, 45, True, True),
            ("07R", "25L", 4000, 45, True, True),
        ],
        "freqs": [
            (FrequencyType.TWR, "Berlin Turm", Decimal("119.700")),
            (FrequencyType.GND, "Berlin Rollkontrolle", Decimal("121.775")),
            (FrequencyType.ATIS, "Berlin ATIS", Decimal("126.925")),
        ],
    },
    {
        "icao": "EDDK", "iata": "CGN",
        "name": "Cologne Bonn Airport", "name_de": "Flughafen Köln/Bonn Konrad Adenauer",
        "city": "Cologne", "city_de": "Köln",
        "region": "North Rhine-Westphalia", "region_de": "Nordrhein-Westfalen",
        "type": AerodromeType.INTERNATIONAL,
        "lat": 50.865833, "lon": 7.142778, "elev_ft": 302,
        "runways": [
            ("14L", "32R", 3815, 45, True, True),
            ("14R", "32L", 2459, 45, False, True),
            ("06", "24", 1863, 45, False, False),
        ],
        "freqs": [
            (FrequencyType.TWR, "Köln Turm", Decimal("118.875")),
            (FrequencyType.GND, "Köln Rollkontrolle", Decimal("121.900")),
            (FrequencyType.ATIS, "Köln ATIS", Decimal("123.125")),
        ],
    },
    {
        "icao": "EDDS", "iata": "STR",
        "name": "Stuttgart Airport", "name_de": "Flughafen Stuttgart Manfred Rommel",
        "city": "Stuttgart", "city_de": "Stuttgart",
        "region": "Baden-Württemberg", "region_de": "Baden-Württemberg",
        "type": AerodromeType.INTERNATIONAL,
        "lat": 48.689722, "lon": 9.221944, "elev_ft": 1276,
        "runways": [
            ("07", "25", 3345, 45, True, True),
        ],
        "freqs": [
            (FrequencyType.TWR, "Stuttgart Turm", Decimal("118.800")),
            (FrequencyType.GND, "Stuttgart Rollkontrolle", Decimal("121.900")),
            (FrequencyType.ATIS, "Stuttgart ATIS", Decimal("126.125")),
        ],
    },
    {
        "icao": "EDDL", "iata": "DUS",
        "name": "Düsseldorf Airport", "name_de": "Flughafen Düsseldorf",
        "city": "Düsseldorf", "city_de": "Düsseldorf",
        "region": "North Rhine-Westphalia", "region_de": "Nordrhein-Westfalen",
        "type": AerodromeType.INTERNATIONAL,
        "lat": 51.289444, "lon": 6.766667, "elev_ft": 147,
        "runways": [
            ("05L", "23R", 3000, 45, True, True),
            ("05R", "23L", 2700, 45, True, False),
        ],
        "freqs": [
            (FrequencyType.TWR, "Düsseldorf Turm", Decimal("118.300")),
            (FrequencyType.GND, "Düsseldorf Rollkontrolle", Decimal("121.900")),
            (FrequencyType.ATIS, "Düsseldorf ATIS", Decimal("123.125")),
        ],
    },
    {
        "icao": "EDDN", "iata": "NUE",
        "name": "Nuremberg Airport", "name_de": "Albrecht Dürer Airport Nürnberg",
        "city": "Nuremberg", "city_de": "Nürnberg",
        "region": "Bavaria", "region_de": "Bayern",
        "type": AerodromeType.INTERNATIONAL,
        "lat": 49.498889, "lon": 11.078333, "elev_ft": 1046,
        "runways": [
            ("10", "28", 2700, 45, True, True),
        ],
        "freqs": [
            (FrequencyType.TWR, "Nürnberg Turm", Decimal("118.900")),
            (FrequencyType.GND, "Nürnberg Rollkontrolle", Decimal("121.750")),
            (FrequencyType.ATIS, "Nürnberg ATIS", Decimal("118.100")),
        ],
    },
    {
        "icao": "EDLW", "iata": "DTM",
        "name": "Dortmund Airport", "name_de": "Dortmund Airport 21",
        "city": "Dortmund", "city_de": "Dortmund",
        "region": "North Rhine-Westphalia", "region_de": "Nordrhein-Westfalen",
        "type": AerodromeType.REGIONAL,
        "lat": 51.518333, "lon": 7.612222, "elev_ft": 425,
        "runways": [
            ("06", "24", 2000, 45, True, True),
        ],
        "freqs": [
            (FrequencyType.TWR, "Dortmund Turm", Decimal("124.350")),
            (FrequencyType.GND, "Dortmund Rollkontrolle", Decimal("121.850")),
            (FrequencyType.ATIS, "Dortmund ATIS", Decimal("118.125")),
        ],
    },
    {
        "icao": "EDDP", "iata": "LEJ",
        "name": "Leipzig/Halle Airport", "name_de": "Flughafen Leipzig/Halle",
        "city": "Leipzig", "city_de": "Leipzig",
        "region": "Saxony", "region_de": "Sachsen",
        "type": AerodromeType.INTERNATIONAL,
        "lat": 51.432222, "lon": 12.241667, "elev_ft": 465,
        "runways": [
            ("08L", "26R", 3600, 60, True, True),
            ("08R", "26L", 3600, 45, True, True),
        ],
        "freqs": [
            (FrequencyType.TWR, "Leipzig Turm", Decimal("126.400")),
            (FrequencyType.GND, "Leipzig Rollkontrolle", Decimal("121.600")),
            (FrequencyType.ATIS, "Leipzig ATIS", Decimal("118.625")),
        ],
    },
]


def main() -> int:
    Session = get_session_factory(database_url())
    session = Session()
    try:
        # Upsert AIRAC cycle
        if session.get(AiracCycle, CYCLE) is None:
            session.add(
                AiracCycle(
                    ident=CYCLE,
                    effective_from=date(2026, 4, 2),
                    effective_to=date(2026, 4, 30),
                    is_current=True,
                )
            )

        added = 0
        skipped = 0
        for ad in AERODROMES:
            if session.get(Aerodrome, ad["icao"]) is not None:
                skipped += 1
                continue
            entity = Aerodrome(
                icao=ad["icao"],
                iata=ad["iata"],
                name=ad["name"],
                name_de=ad["name_de"],
                city=ad["city"],
                city_de=ad["city_de"],
                region=ad["region"],
                region_de=ad["region_de"],
                country="DE",
                type=ad["type"],
                latitude=ad["lat"],
                longitude=ad["lon"],
                elevation_ft=ad["elev_ft"],
                source_airac_cycle=CYCLE,
            )
            for le, he, length_m, width_m, ils_le, ils_he in ad["runways"]:
                entity.runways.append(
                    Runway(
                        designator_le=le,
                        designator_he=he,
                        length_m=length_m,
                        width_m=width_m,
                        surface=RunwaySurface.ASPHALT,
                        ils_le=ils_le,
                        ils_he=ils_he,
                        source_airac_cycle=CYCLE,
                    )
                )
            for freq_type, callsign, mhz in ad["freqs"]:
                entity.frequencies.append(
                    Frequency(
                        type=freq_type,
                        callsign=callsign,
                        callsign_de=callsign,
                        frequency_mhz=mhz,
                        source_airac_cycle=CYCLE,
                    )
                )
            session.add(entity)
            added += 1

        session.commit()
        print(f"OK  aerodromes added   : {added}")
        print(f"OK  aerodromes skipped : {skipped} (already present)")
        total = session.query(Aerodrome).count()
        print(f"OK  total in DB        : {total}")
        return 0
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        print(f"FAIL seed             : {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
