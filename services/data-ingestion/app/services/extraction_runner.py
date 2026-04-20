"""Per-aerodrome extraction runner.

Runs the 2-of-2 Claude+OpenAI vision pipeline on the ranked VFR chart
candidates and writes consensus results to the ingest DB tables.

Scope (MVP, for #34):
  - field_groups written to DB: geo, runways, frequencies.
  - obstacles + reporting_points extracted for the audit trail but not
    persisted (no DB tables yet — follow-up issue).

Progress tracking: updates ``ingest.extraction_jobs`` after each field
group so the UI can poll and display a realistic step indicator.

Errors never abort the whole job; they're recorded per-field-group so
the user can see partial successes (e.g. runways succeeded, obstacles
failed with rate-limit).
"""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

from shared.schemas.enums import FrequencyType, RunwaySurface
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import (
    Aerodrome,
    ExtractionJob,
    Frequency,
    Runway,
)
from app.parser.chart_selector import rank_charts
from app.parser.providers.base import (
    ExtractionProvider,
    FieldGroup,
    ProviderNotConfigured,
)

log = logging.getLogger(__name__)

DATA_ROOT = Path("/app/data/aerodromes")

# How many candidate charts to cascade through per field group before giving up.
MAX_CANDIDATES_PER_GROUP = 3

# Field groups the runner executes, in the order the progress bar shows them.
PIPELINE_FIELD_GROUPS: tuple[FieldGroup, ...] = (
    "geo",
    "runways",
    "frequencies",
    "obstacles",
    "reporting_points",
)


class ExtractionRunner:
    """Orchestrates one extraction job for one aerodrome.

    Instantiated per-job by the FastAPI BackgroundTasks handler. Holds no
    state between jobs. DB session lifetime is scoped to the runner.
    """

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        providers: list[ExtractionProvider],
        data_root: Path = DATA_ROOT,
    ) -> None:
        self._session_factory = session_factory
        self._providers = providers
        self._data_root = data_root

    # ------------------------------------------------------------------ #
    # Public entry
    # ------------------------------------------------------------------ #

    def run(self, job_id: UUID, icao: str) -> None:
        icao = icao.upper()
        session = self._session_factory()
        try:
            job = session.get(ExtractionJob, job_id)
            if job is None:
                log.error("ExtractionJob %s not found; aborting runner", job_id)
                return

            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            job.current_step = f"Starte Extraktion für {icao}"
            session.commit()
        except Exception:
            session.rollback()
            log.exception("Failed to mark job %s as running", job_id)
            session.close()
            return

        try:
            self._run_pipeline(session, job, icao)
            job.status = "completed"
            job.progress_pct = 100
            job.current_step = "Fertig"
            job.completed_at = datetime.now(timezone.utc)
            session.commit()
        except Exception as exc:
            log.exception("Extraction job %s failed", job_id)
            session.rollback()
            try:
                job.status = "failed"
                job.error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[-600:]}"
                job.completed_at = datetime.now(timezone.utc)
                session.commit()
            except Exception:
                session.rollback()
        finally:
            session.close()

    # ------------------------------------------------------------------ #
    # Pipeline
    # ------------------------------------------------------------------ #

    def _run_pipeline(self, session: Session, job: ExtractionJob, icao: str) -> None:
        aerodrome = session.execute(
            select(Aerodrome).where(Aerodrome.icao == icao)
        ).scalar_one_or_none()
        if aerodrome is None:
            raise RuntimeError(f"Aerodrome {icao} does not exist in ingest.aerodromes")

        configured = [p for p in self._providers if p.is_configured()]
        if len(configured) < 2:
            raise RuntimeError(
                "Fewer than 2 providers configured — 2-of-2 consensus is unreachable"
            )

        aerodrome_dir = self._data_root / icao
        total_groups = len(PIPELINE_FIELD_GROUPS)
        groups_completed: dict[str, Any] = {}
        fields_written = 0

        for idx, field_group in enumerate(PIPELINE_FIELD_GROUPS, start=1):
            self._report_progress(
                session, job,
                pct=int(((idx - 1) / total_groups) * 95),  # keep last 5% for writes
                step=f"Extrahiere {field_group} ({idx}/{total_groups})",
            )

            candidates = rank_charts(aerodrome_dir, field_group=field_group)
            if not candidates:
                groups_completed[field_group] = {"status": "no_candidates"}
                continue

            accepted_parsed_a, accepted_parsed_b, accepted_chart = None, None, None
            for candidate in candidates[:MAX_CANDIDATES_PER_GROUP]:
                self._report_progress(
                    session, job,
                    pct=int(((idx - 1) / total_groups) * 95),
                    step=f"{field_group} ← {candidate.path.name}",
                )
                parsed_a, parsed_b, err = self._call_both_providers(
                    configured, candidate.path, field_group, icao
                )
                if err:
                    # Keep trying the next candidate on transient failure.
                    groups_completed.setdefault(field_group, {})["last_error"] = err
                    continue
                if _has_signal(parsed_a) and _has_signal(parsed_b):
                    accepted_parsed_a = parsed_a
                    accepted_parsed_b = parsed_b
                    accepted_chart = candidate.path.name
                    break

            if accepted_parsed_a is None:
                groups_completed[field_group] = {
                    "status": "no_consensus",
                    "candidates_tried": len(candidates[:MAX_CANDIDATES_PER_GROUP]),
                }
                continue

            written = self._persist_field_group(
                session, aerodrome, field_group,
                parsed_a=accepted_parsed_a, parsed_b=accepted_parsed_b,
            )
            fields_written += written
            groups_completed[field_group] = {
                "status": "accepted",
                "accepted_chart": accepted_chart,
                "fields_written": written,
            }
            # Commit after each group so progress reflects actual DB state.
            session.commit()

            self._report_progress(
                session, job,
                pct=int((idx / total_groups) * 95),
                step=f"{field_group} abgeschlossen ({written} Felder geschrieben)",
            )

        job.field_groups_completed = groups_completed
        job.fields_written = fields_written
        session.commit()

    def _call_both_providers(
        self,
        providers: list[ExtractionProvider],
        image_path: Path,
        field_group: FieldGroup,
        icao: str,
    ) -> tuple[dict | None, dict | None, str | None]:
        """Call both providers for one chart. Return (parsed_a, parsed_b, error_or_None)."""
        parsed: dict[str, dict] = {}
        for p in providers:
            try:
                result = p.extract(
                    image_path=image_path,
                    field_group=field_group,
                    aerodrome_icao=icao,
                )
                parsed[p.name] = result.raw_response.get("parsed")
            except ProviderNotConfigured:
                return None, None, f"{p.name} not configured"
            except Exception as exc:
                return None, None, f"{p.name}: {type(exc).__name__}: {str(exc)[:120]}"
        # The two registered providers come in order Claude, OpenAI — but
        # pick them by name to stay robust if config changes.
        a = next((v for k, v in parsed.items() if k.startswith("claude")), None)
        b = next((v for k, v in parsed.items() if k.startswith("openai")), None)
        return a, b, None

    def _report_progress(
        self,
        session: Session,
        job: ExtractionJob,
        *,
        pct: int,
        step: str,
    ) -> None:
        job.progress_pct = max(0, min(95, pct))
        job.current_step = step[:200]
        session.commit()

    # ------------------------------------------------------------------ #
    # Persistence — one function per field group
    # ------------------------------------------------------------------ #

    def _persist_field_group(
        self,
        session: Session,
        aerodrome: Aerodrome,
        field_group: FieldGroup,
        *,
        parsed_a: dict,
        parsed_b: dict,
    ) -> int:
        if field_group == "geo":
            return _persist_geo(aerodrome, parsed_a, parsed_b)
        if field_group == "runways":
            return _persist_runways(session, aerodrome, parsed_a, parsed_b)
        if field_group == "frequencies":
            return _persist_frequencies(session, aerodrome, parsed_a, parsed_b)
        # obstacles / reporting_points: no DB tables yet → audit only.
        return 0


# ---------------------------------------------------------------------------
# Pure helpers (module-level so they're unit-testable without the runner)
# ---------------------------------------------------------------------------

def _has_signal(parsed: Any) -> bool:
    """True iff at least one ExtractedValue in `parsed` has a non-null `value`."""
    if parsed is None:
        return False
    if isinstance(parsed, dict):
        if "value" in parsed and parsed.get("value") is not None:
            return True
        return any(_has_signal(v) for v in parsed.values())
    if isinstance(parsed, list):
        return any(_has_signal(item) for item in parsed)
    return False


def _unwrap(value: Any) -> Any:
    """Drop the {value, bbox, note} wrapper if present; otherwise return as-is."""
    if isinstance(value, dict) and "value" in value and "bbox" in value:
        return value.get("value")
    return value


def _agree(a: Any, b: Any, *, float_tol: float = 0.01) -> Any | None:
    """Return the agreed value if a == b (within float_tol), else None."""
    a = _unwrap(a)
    b = _unwrap(b)
    if a is None or b is None:
        return None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) if abs(float(a) - float(b)) <= float_tol else None
    sa, sb = str(a).strip(), str(b).strip()
    if sa.lower() == sb.lower():
        return sa
    # Loose match: drop internal whitespace
    if "".join(sa.split()).lower() == "".join(sb.split()).lower():
        return sa
    return None


def _persist_geo(aerodrome: Aerodrome, a: dict, b: dict) -> int:
    """Update aerodrome columns in-place where both providers agree."""
    written = 0

    lat = _agree(a.get("latitude_deg"), b.get("latitude_deg"), float_tol=0.001)
    if lat is not None:
        aerodrome.latitude = float(lat)
        written += 1

    lon = _agree(a.get("longitude_deg"), b.get("longitude_deg"), float_tol=0.001)
    if lon is not None:
        aerodrome.longitude = float(lon)
        written += 1

    elev = _agree_int_with_unit(a.get("elevation_ft"), b.get("elevation_ft"))
    if elev is not None:
        aerodrome.elevation_ft = elev
        written += 1

    magvar = _agree(
        a.get("magnetic_variation_deg"),
        b.get("magnetic_variation_deg"),
        float_tol=0.5,
    )
    if magvar is not None:
        try:
            aerodrome.magnetic_variation = Decimal(str(magvar))
            written += 1
        except InvalidOperation:
            pass

    for field in ("operator", "operator_de", "city", "city_de"):
        agreed = _agree(a.get(field), b.get(field))
        if agreed is not None and getattr(aerodrome, field) != agreed:
            setattr(aerodrome, field, agreed)
            written += 1

    return written


def _agree_int_with_unit(a: Any, b: Any) -> int | None:
    """Handle elevation-style values like '1487 FT' or '453 M' — strip unit, compare ints."""
    av = _unwrap(a)
    bv = _unwrap(b)
    if av is None or bv is None:
        return None
    ai = _parse_first_int(av)
    bi = _parse_first_int(bv)
    if ai is None or bi is None:
        return None
    return ai if abs(ai - bi) <= 2 else None  # 2 ft slack for rounding


def _parse_first_int(s: Any) -> int | None:
    if isinstance(s, (int,)):
        return int(s)
    if isinstance(s, float):
        return int(s)
    if not isinstance(s, str):
        return None
    import re
    m = re.search(r"-?\d+", s.replace(",", ""))
    return int(m.group()) if m else None


def _persist_runways(session: Session, aerodrome: Aerodrome, a: dict, b: dict) -> int:
    """Replace aerodrome's runway rows with agreed-on entries."""
    rws_a = a.get("runways") or []
    rws_b = b.get("runways") or []

    # Pair up by designator_le — if both providers list a 08L, compare those.
    def keyed(lst):
        out: dict[str, dict] = {}
        for rw in lst:
            le = _unwrap(rw.get("designator_le"))
            if le:
                out[str(le).upper()] = rw
        return out

    keyed_a = keyed(rws_a)
    keyed_b = keyed(rws_b)

    agreed_rows = []
    for le, rw_a in keyed_a.items():
        rw_b = keyed_b.get(le)
        if rw_b is None:
            continue
        le_agreed = _agree(rw_a.get("designator_le"), rw_b.get("designator_le"))
        he_agreed = _agree(rw_a.get("designator_he"), rw_b.get("designator_he"))
        if not le_agreed or not he_agreed:
            continue
        length_m = _agree_int_with_unit(rw_a.get("length_m"), rw_b.get("length_m"))
        width_m = _agree_int_with_unit(rw_a.get("width_m"), rw_b.get("width_m"))
        surface_raw = _agree(rw_a.get("surface"), rw_b.get("surface"))
        surface = _map_surface(surface_raw) if surface_raw else RunwaySurface.OTHER
        agreed_rows.append({
            "designator_le": str(le_agreed).upper(),
            "designator_he": str(he_agreed).upper(),
            "length_m": length_m,
            "width_m": width_m,
            "surface": surface,
        })

    if not agreed_rows:
        return 0

    session.execute(
        delete(Runway).where(Runway.aerodrome_icao == aerodrome.icao)
    )
    session.flush()

    airac = aerodrome.source_airac_cycle
    for row in agreed_rows:
        session.add(Runway(
            aerodrome_icao=aerodrome.icao,
            source_airac_cycle=airac,
            **row,
        ))
    return len(agreed_rows)


def _map_surface(raw: str | None) -> RunwaySurface:
    if not raw:
        return RunwaySurface.OTHER
    token = str(raw).strip().lower()
    # Direct enum match
    for surf in RunwaySurface:
        if surf.value == token:
            return surf
    # Best-effort mapping for compound / German terms
    if "asph" in token or "bitum" in token:
        return RunwaySurface.ASPHALT
    if "beton" in token or "conc" in token:
        return RunwaySurface.CONCRETE
    if "gras" in token or "grass" in token:
        return RunwaySurface.GRASS
    if "gravel" in token or "schotter" in token:
        return RunwaySurface.GRAVEL
    return RunwaySurface.OTHER


def _persist_frequencies(session: Session, aerodrome: Aerodrome, a: dict, b: dict) -> int:
    """Replace aerodrome's frequency rows with agreed-on entries."""
    a_list = a.get("frequencies") or []
    b_list = b.get("frequencies") or []

    # Pair by (type, frequency_mhz) — the canonical identity of a freq row.
    def keyed(lst):
        out: dict[tuple[str, str], dict] = {}
        for item in lst:
            t = _unwrap(item.get("type"))
            f = _unwrap(item.get("frequency_mhz"))
            if t and f:
                out[(str(t).strip().lower(), str(f).strip())] = item
        return out

    keyed_a = keyed(a_list)
    keyed_b = keyed(b_list)

    agreed: list[dict] = []
    for key, item_a in keyed_a.items():
        item_b = keyed_b.get(key)
        if item_b is None:
            continue
        t_raw, f_raw = key
        try:
            freq = Decimal(f_raw)
        except InvalidOperation:
            continue
        ft = _map_freq_type(t_raw)
        if ft is None:
            continue
        callsign = _agree(item_a.get("callsign"), item_b.get("callsign"))
        callsign_de = _agree(item_a.get("callsign_de"), item_b.get("callsign_de"))
        hours = _agree(item_a.get("operational_hours"), item_b.get("operational_hours"))
        agreed.append({
            "type": ft,
            "frequency_mhz": freq,
            "callsign": callsign,
            "callsign_de": callsign_de,
            "operational_hours": hours,
        })

    if not agreed:
        return 0

    session.execute(
        delete(Frequency).where(Frequency.aerodrome_icao == aerodrome.icao)
    )
    session.flush()

    airac = aerodrome.source_airac_cycle
    for row in agreed:
        session.add(Frequency(
            aerodrome_icao=aerodrome.icao,
            source_airac_cycle=airac,
            **row,
        ))
    return len(agreed)


def _map_freq_type(token: str) -> FrequencyType | None:
    token = token.strip().lower()
    for ft in FrequencyType:
        if ft.value == token:
            return ft
    # Fallbacks for prompt-output variants
    alias = {
        "tower": FrequencyType.TWR,
        "ground": FrequencyType.GND,
        "approach": FrequencyType.APP,
        "departure": FrequencyType.DEP,
        "delivery": FrequencyType.DEL,
        "information": FrequencyType.INFO,
    }
    return alias.get(token)
