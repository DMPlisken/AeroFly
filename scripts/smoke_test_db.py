"""Round-trip smoke test for the ingest schema.

Inserts a synthetic EDDM aerodrome with one runway, three frequencies, one
chart, and one NOTAM; reads them back; prints a summary; then rolls back so
the database is left unchanged.

Run from the project root after `alembic upgrade head`:

    DATABASE_URL=postgresql://aerofly:changeme@localhost:5432/aerofly \
        python scripts/smoke_test_db.py
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# Make `shared.python.*` importable when running from repo root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "services" / "data-ingestion"))

# Alias `shared.*` -> `shared.python.*` so the service models (which import
# `shared.schemas.enums` as they would inside the container) work locally.
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
from app.db.models import (  # noqa: E402
    Aerodrome,
    AiracCycle,
    Chart,
    Frequency,
    Notam,
    Runway,
)
from shared.python.schemas.enums import (  # noqa: E402
    AerodromeType,
    ChartType,
    FrequencyType,
    NotamCategory,
    NotamPurpose,
    NotamScope,
    NotamSeverity,
    NotamTraffic,
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


def main() -> int:
    Session = get_session_factory(database_url())
    session = Session()
    try:
        cycle = AiracCycle(
            ident="2026-04",
            effective_from=date(2026, 4, 2),
            effective_to=date(2026, 4, 30),
            is_current=True,
        )
        session.add(cycle)
        session.flush()

        ad = Aerodrome(
            icao="ZZZZ",
            iata="ZZZ",
            name="Smoketest Airport",
            name_de="Smoketest Flughafen",
            city="Testville",
            city_de="Testburg",
            region="Bavaria",
            region_de="Bayern",
            country="DE",
            type=AerodromeType.INTERNATIONAL,
            latitude=48.3538,
            longitude=11.7861,
            elevation_ft=1487,
            magnetic_variation=Decimal("2.50"),
            source_airac_cycle=cycle.ident,
        )
        session.add(ad)
        session.flush()

        session.add_all(
            [
                Runway(
                    aerodrome_icao=ad.icao,
                    designator_le="08L",
                    designator_he="26R",
                    length_m=4000,
                    width_m=60,
                    surface=RunwaySurface.ASPHALT,
                    ils_le=True,
                    ils_he=True,
                    source_airac_cycle=cycle.ident,
                ),
                Frequency(
                    aerodrome_icao=ad.icao,
                    type=FrequencyType.TWR,
                    callsign="Smoketest Tower",
                    callsign_de="Smoketest Turm",
                    frequency_mhz=Decimal("118.700"),
                    source_airac_cycle=cycle.ident,
                ),
                Frequency(
                    aerodrome_icao=ad.icao,
                    type=FrequencyType.GND,
                    callsign="Smoketest Ground",
                    frequency_mhz=Decimal("121.700"),
                    source_airac_cycle=cycle.ident,
                ),
                Frequency(
                    aerodrome_icao=ad.icao,
                    type=FrequencyType.ATIS,
                    frequency_mhz=Decimal("123.125"),
                    source_airac_cycle=cycle.ident,
                ),
                Chart(
                    aerodrome_icao=ad.icao,
                    chart_type=ChartType.AD_CHART,
                    title="Aerodrome Chart 10-9",
                    title_de="Flughafenkarte 10-9",
                    source_url="https://example.test/smoke/ad-10-9.pdf",
                    language="de",
                    source_airac_cycle=cycle.ident,
                ),
            ]
        )
        session.add(
            Notam(
                notam_id="A0001/99",
                aerodrome_icao=ad.icao,
                fir="EDMM",
                category=NotamCategory.NEW,
                severity=NotamSeverity.HIGH,
                q_fir="EDMM",
                q_code="QMRLC",
                q_traffic=NotamTraffic.IFR_VFR,
                q_purpose=[NotamPurpose.BO],
                q_scope=[NotamScope.AERODROME],
                q_lower_limit_ft=0,
                q_upper_limit_ft=999,
                q_coords_lat=48.3538,
                q_coords_lon=11.7861,
                q_radius_nm=5,
                a_location="ZZZZ",
                b_valid_from=datetime.now(tz=timezone.utc),
                c_valid_to=datetime.now(tz=timezone.utc) + timedelta(hours=6),
                e_condition="Smoke test NOTAM — runway inspection in progress.",
                e_condition_de="Rauchtest-NOTAM — Bahninspektion im Gange.",
                raw_text="A0001/99 NOTAMN ...",
                source_airac_cycle=cycle.ident,
            )
        )
        session.flush()

        # Read back
        loaded = (
            session.query(Aerodrome).filter(Aerodrome.icao == "ZZZZ").one()
        )
        print(f"OK  aerodrome          : {loaded.icao} / {loaded.name} / {loaded.name_de}")
        print(f"OK  runways            : {len(loaded.runways)}")
        print(f"OK  frequencies        : {len(loaded.frequencies)}")
        print(f"OK  charts             : {len(loaded.charts)}")
        print(f"OK  notams             : {len(loaded.notams)}")
        print(f"OK  airac cycle        : {loaded.source_airac_cycle}")

        session.rollback()
        print("OK  rollback           : clean — no data persisted")
        return 0
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        print(f"FAIL smoke test       : {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
