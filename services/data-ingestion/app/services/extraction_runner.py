"""Per-aerodrome extraction runner (multi-chart aggregation).

Runs the 2-of-2 Claude+OpenAI vision pipeline on every acceptable VFR
chart for each field group and **merges** results across charts. Writes
consensus values to the ingest DB tables.

Design (revised for #36)
------------------------

Problem with the first-wins cascade used in #35: German airports spread
data across several charts (e.g. EDDF prints parallel runway pair on
chart 2 and the cross-runway on chart 3; frequency box sits on the
Terminal Chart; elevation may appear on the VAC but not the ADC). The
original runner stopped at the first chart that had any signal and
missed everything on the others.

Revised semantics:

- **List-valued field groups** (runways, frequencies, obstacles,
  reporting_points): iterate ALL acceptable candidates. Per chart,
  compute same-chart 2-of-2 consensus entries. Across charts, take the
  union keyed by natural identity (`designator_le` for runways,
  `(type, frequency_mhz)` for frequencies). First-seen wins for an
  individual key — later charts don't overwrite.

- **Scalar field group** (geo): iterate candidates. Per chart, compute
  the dict of agreed-upon fields (`_agreed_geo_on_chart`). Merge into
  the accumulator by filling gaps only — earlier accepted values stand.
  Stop early once every scalar field has been filled.

- **Same-chart consensus** is preserved. We never let Claude on chart A
  + OpenAI on chart B "agree" on something — that would chain
  hallucinations across independent pages.

- `obstacles` and `reporting_points` are extracted but not persisted
  (no DB tables yet — separate issue).

Failure semantics: errors per chart don't abort the job. The field
group records the last transient error in `field_groups_completed`
for the user to see.
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

# Safety cap against runaway API spend. Typical German VFR airport has
# 4–8 acceptable charts; 10 is plenty.
MAX_CANDIDATES_PER_GROUP = 10

# Field groups the runner executes, in the order the progress bar shows them.
PIPELINE_FIELD_GROUPS: tuple[FieldGroup, ...] = (
    "geo",
    "runways",
    "frequencies",
    "obstacles",
    "reporting_points",
)

# All scalar fields the geo runner may fill. Order matters only for the
# early-exit heuristic.
_GEO_FIELDS: tuple[str, ...] = (
    "latitude_deg",
    "longitude_deg",
    "elevation_ft",
    "magnetic_variation_deg",
    "operator",
    "operator_de",
    "city",
    "city_de",
)


class ExtractionRunner:
    """Orchestrates one extraction job for one aerodrome.

    Instantiated per-job by the FastAPI BackgroundTasks handler. Holds
    no state between jobs. DB session lifetime is scoped to the runner.
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
        fields_written_total = 0

        for idx, field_group in enumerate(PIPELINE_FIELD_GROUPS, start=1):
            base_pct = int(((idx - 1) / total_groups) * 95)
            self._report_progress(session, job, pct=base_pct,
                                  step=f"Extrahiere {field_group} ({idx}/{total_groups})")

            candidates = rank_charts(aerodrome_dir, field_group=field_group)
            candidates = candidates[:MAX_CANDIDATES_PER_GROUP]
            if not candidates:
                groups_completed[field_group] = {"status": "no_candidates"}
                continue

            if field_group == "geo":
                written, details = self._run_geo(
                    session, job, configured, aerodrome, candidates, base_pct, icao,
                )
            elif field_group == "runways":
                written, details = self._run_runways(
                    session, job, configured, aerodrome, candidates, base_pct, icao,
                )
            elif field_group == "frequencies":
                written, details = self._run_frequencies(
                    session, job, configured, aerodrome, candidates, base_pct, icao,
                )
            else:
                # obstacles / reporting_points — run for audit trail but skip persist.
                written, details = self._run_audit_only(
                    job, configured, candidates, base_pct, icao, field_group, session,
                )

            groups_completed[field_group] = details
            fields_written_total += written
            session.commit()

            self._report_progress(
                session, job,
                pct=int((idx / total_groups) * 95),
                step=f"{field_group}: {written} Feld(er) geschrieben",
            )

        job.field_groups_completed = groups_completed
        job.fields_written = fields_written_total
        session.commit()

    # ------------------------------------------------------------------ #
    # Per-field-group runners (aggregate across candidates)
    # ------------------------------------------------------------------ #

    def _run_geo(
        self, session, job, providers, aerodrome, candidates, base_pct, icao,
    ):
        accumulator: dict[str, Any] = {}
        charts_used: list[str] = []
        errors: list[str] = []
        for i, cand in enumerate(candidates, start=1):
            if set(accumulator.keys()) >= set(_GEO_FIELDS):
                break  # every scalar field filled — no point running more charts
            self._report_progress(
                session, job, pct=base_pct,
                step=f"geo ← {cand.path.name} ({i}/{len(candidates)})",
            )
            a, b, err = self._call_both_providers(providers, cand.path, "geo", icao)
            if err:
                errors.append(err)
                continue
            agreed = _agreed_geo_on_chart(a or {}, b or {})
            if not agreed:
                continue
            filled_here = False
            for field, value in agreed.items():
                if field in accumulator or value is None:
                    continue
                accumulator[field] = value
                filled_here = True
            if filled_here and cand.path.name not in charts_used:
                charts_used.append(cand.path.name)
        written = _apply_geo_dict(aerodrome, accumulator)
        return written, {
            "status": "accepted" if written else "no_consensus",
            "accepted_charts": charts_used,
            "fields_written": written,
            "last_error": errors[-1] if errors else None,
        }

    def _run_runways(
        self, session, job, providers, aerodrome, candidates, base_pct, icao,
    ):
        merged: dict[str, dict] = {}
        charts_used: list[str] = []
        errors: list[str] = []
        for i, cand in enumerate(candidates, start=1):
            self._report_progress(
                session, job, pct=base_pct,
                step=f"runways ← {cand.path.name} ({i}/{len(candidates)})",
            )
            a, b, err = self._call_both_providers(providers, cand.path, "runways", icao)
            if err:
                errors.append(err)
                continue
            entries = _agreed_runways_on_chart(a or {}, b or {})
            added_any = False
            for entry in entries:
                key = entry["designator_le"]
                if key not in merged:
                    merged[key] = entry
                    added_any = True
            if added_any and cand.path.name not in charts_used:
                charts_used.append(cand.path.name)
        written = _write_runways(session, aerodrome, list(merged.values()))
        return written, {
            "status": "accepted" if written else "no_consensus",
            "accepted_charts": charts_used,
            "fields_written": written,
            "last_error": errors[-1] if errors else None,
        }

    def _run_frequencies(
        self, session, job, providers, aerodrome, candidates, base_pct, icao,
    ):
        merged: dict[tuple, dict] = {}
        charts_used: list[str] = []
        errors: list[str] = []
        for i, cand in enumerate(candidates, start=1):
            self._report_progress(
                session, job, pct=base_pct,
                step=f"frequencies ← {cand.path.name} ({i}/{len(candidates)})",
            )
            a, b, err = self._call_both_providers(providers, cand.path, "frequencies", icao)
            if err:
                errors.append(err)
                continue
            entries = _agreed_frequencies_on_chart(a or {}, b or {})
            added_any = False
            for entry in entries:
                key = (entry["type"], str(entry["frequency_mhz"]))
                if key not in merged:
                    merged[key] = entry
                    added_any = True
            if added_any and cand.path.name not in charts_used:
                charts_used.append(cand.path.name)
        written = _write_frequencies(session, aerodrome, list(merged.values()))
        return written, {
            "status": "accepted" if written else "no_consensus",
            "accepted_charts": charts_used,
            "fields_written": written,
            "last_error": errors[-1] if errors else None,
        }

    def _run_audit_only(
        self, job, providers, candidates, base_pct, icao, field_group, session,
    ):
        errors: list[str] = []
        saw_signal = False
        for i, cand in enumerate(candidates, start=1):
            self._report_progress(
                session, job, pct=base_pct,
                step=f"{field_group} ← {cand.path.name} ({i}/{len(candidates)})",
            )
            a, b, err = self._call_both_providers(providers, cand.path, field_group, icao)
            if err:
                errors.append(err)
                continue
            if _has_signal(a) and _has_signal(b):
                saw_signal = True
        return 0, {
            "status": "audit_only_signal_seen" if saw_signal else "audit_only_no_signal",
            "last_error": errors[-1] if errors else None,
            "note": "DB persistence not yet implemented",
        }

    # ------------------------------------------------------------------ #
    # Provider fan-out
    # ------------------------------------------------------------------ #

    def _call_both_providers(
        self,
        providers: list[ExtractionProvider],
        image_path: Path,
        field_group: FieldGroup,
        icao: str,
    ) -> tuple[dict | None, dict | None, str | None]:
        """Call both providers for one chart. Return (parsed_a, parsed_b, error_or_None).

        One provider failing on a chart disqualifies the chart from 2-of-2
        consensus, but does not abort the entire job — the runner moves on
        to the next candidate. We log the full exception detail here so
        the root cause is visible in docker logs even though the audit row
        only keeps the first 400 chars.
        """
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
                log.exception(
                    "Provider %s failed on %s for %s",
                    p.name, image_path.name, field_group,
                )
                return (
                    None, None,
                    f"{p.name} on {image_path.name}: "
                    f"{type(exc).__name__}: {str(exc)[:400]}",
                )
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


# ---------------------------------------------------------------------------
# Pure helpers — per-chart consensus
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
    if "".join(sa.split()).lower() == "".join(sb.split()).lower():
        return sa
    return None


def _agree_int_with_unit(a: Any, b: Any) -> int | None:
    """Elevation-style values like '1487 FT' or '453 M' — strip unit, compare ints."""
    av = _unwrap(a)
    bv = _unwrap(b)
    if av is None or bv is None:
        return None
    ai = _parse_first_int(av)
    bi = _parse_first_int(bv)
    if ai is None or bi is None:
        return None
    return ai if abs(ai - bi) <= 2 else None


def _parse_first_int(s: Any) -> int | None:
    if isinstance(s, int):
        return int(s)
    if isinstance(s, float):
        return int(s)
    if not isinstance(s, str):
        return None
    import re
    m = re.search(r"-?\d+", s.replace(",", ""))
    return int(m.group()) if m else None


def _agreed_geo_on_chart(a: dict, b: dict) -> dict[str, Any]:
    """Return the dict of scalar fields both providers agreed on for ONE chart."""
    out: dict[str, Any] = {}
    lat = _agree(a.get("latitude_deg"), b.get("latitude_deg"), float_tol=0.001)
    if lat is not None:
        out["latitude_deg"] = float(lat)
    lon = _agree(a.get("longitude_deg"), b.get("longitude_deg"), float_tol=0.001)
    if lon is not None:
        out["longitude_deg"] = float(lon)
    elev = _agree_int_with_unit(a.get("elevation_ft"), b.get("elevation_ft"))
    if elev is not None:
        out["elevation_ft"] = elev
    magvar = _agree(
        a.get("magnetic_variation_deg"), b.get("magnetic_variation_deg"),
        float_tol=0.5,
    )
    if magvar is not None:
        try:
            out["magnetic_variation_deg"] = Decimal(str(magvar))
        except InvalidOperation:
            pass
    for field in ("operator", "operator_de", "city", "city_de"):
        agreed = _agree(a.get(field), b.get(field))
        if agreed is not None:
            out[field] = agreed
    return out


_OPPOSITE_SUFFIX = {"L": "R", "R": "L", "C": "C", "": ""}


def _opposite_designator(le: str) -> str | None:
    """Compute the high-end designator from a low-end one.

    Runway designators are always 180° apart: `08L` ↔ `26R`, `07C` ↔ `25C`,
    `18` ↔ `36`. Returns None if the input doesn't look like a designator.
    """
    import re
    m = re.match(r"^\s*(\d{1,2})\s*([LRC]?)\s*$", str(le).upper())
    if not m:
        return None
    try:
        n = int(m.group(1))
    except ValueError:
        return None
    if not (1 <= n <= 36):
        return None
    opp_num = ((n + 17) % 36) + 1  # 1..36 with 36 wrapping to 18, 18 to 36, etc.
    suf = _OPPOSITE_SUFFIX.get(m.group(2), "")
    return f"{opp_num:02d}{suf}"


def _resolve_he(rw_a: dict, rw_b: dict, le: str) -> str | None:
    """Pick the high-end designator, tolerating missing HE from ONE provider.

    Safety rules:
      1. Both provided HE AND they agree → use the agreed value.
      2. Both provided HE AND they disagree → reject (don't use LE-math
         to break the tie; a provider misread).
      3. Only one provided HE AND it matches the mathematical opposite
         of LE → accept (runway identity is safe; the other provider
         simply dropped the field, which we've observed on EDDF).
      4. Only one provided HE but it doesn't match computed opposite →
         reject (inconsistent with the agreed LE).
      5. Neither provided HE → compute from LE.

    Returns None when no safe HE is resolvable.
    """
    a_he = _unwrap(rw_a.get("designator_he"))
    b_he = _unwrap(rw_b.get("designator_he"))

    # Rule 1 & 2 — both sides reported HE.
    if a_he is not None and b_he is not None:
        agreed = _agree(
            {"value": a_he, "bbox": None},
            {"value": b_he, "bbox": None},
        )
        return str(agreed).upper() if agreed else None

    # Rules 3–5 — at least one side dropped HE. Fall back to LE math.
    computed = _opposite_designator(le)
    if computed is None:
        return None
    provided = a_he if a_he is not None else b_he
    if provided is not None and str(provided).upper() != computed:
        return None
    return computed


def _agreed_runways_on_chart(a: dict, b: dict) -> list[dict]:
    """Return runway dicts both providers agreed on for ONE chart.

    Relaxed rule for `designator_he`: the opposite-end designator is
    mathematically determined by the low-end (always 180° apart), so if
    both providers agree on LE we accept the runway and auto-derive HE
    when providers disagree or one is null. This recovers cases where
    OpenAI drops the HE (observed on EDDF chart 2 runway 18).
    """
    rws_a = a.get("runways") or []
    rws_b = b.get("runways") or []

    def keyed(lst):
        out: dict[str, dict] = {}
        for rw in lst:
            le = _unwrap(rw.get("designator_le"))
            if le:
                out[str(le).upper()] = rw
        return out

    keyed_a = keyed(rws_a)
    keyed_b = keyed(rws_b)

    agreed: list[dict] = []
    for le, rw_a in keyed_a.items():
        rw_b = keyed_b.get(le)
        if rw_b is None:
            continue
        le_agreed = _agree(rw_a.get("designator_le"), rw_b.get("designator_le"))
        if not le_agreed:
            continue
        he_agreed = _resolve_he(rw_a, rw_b, str(le_agreed).upper())
        if not he_agreed:
            continue
        length_m = _agree_int_with_unit(rw_a.get("length_m"), rw_b.get("length_m"))
        width_m = _agree_int_with_unit(rw_a.get("width_m"), rw_b.get("width_m"))
        surface_raw = _agree(rw_a.get("surface"), rw_b.get("surface"))
        surface = _map_surface(surface_raw) if surface_raw else RunwaySurface.OTHER
        agreed.append({
            "designator_le": str(le_agreed).upper(),
            "designator_he": he_agreed,
            "length_m": length_m,
            "width_m": width_m,
            "surface": surface,
        })
    return agreed


def _agreed_frequencies_on_chart(a: dict, b: dict) -> list[dict]:
    """Return frequency dicts both providers agreed on for ONE chart."""
    a_list = a.get("frequencies") or []
    b_list = b.get("frequencies") or []

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
    return agreed


# ---------------------------------------------------------------------------
# DB writes — take aggregated results, replace target tables
# ---------------------------------------------------------------------------

def _apply_geo_dict(aerodrome: Aerodrome, geo: dict[str, Any]) -> int:
    """Apply the merged geo dict to the aerodrome row. Returns fields changed."""
    written = 0
    mapping = {
        "latitude_deg": ("latitude", float),
        "longitude_deg": ("longitude", float),
        "elevation_ft": ("elevation_ft", int),
        "magnetic_variation_deg": ("magnetic_variation", None),  # Decimal already
        "operator": ("operator", str),
        "operator_de": ("operator_de", str),
        "city": ("city", str),
        "city_de": ("city_de", str),
    }
    for src, (attr, caster) in mapping.items():
        if src not in geo:
            continue
        value = geo[src]
        if caster and not isinstance(value, caster):
            try:
                value = caster(value)
            except (TypeError, ValueError):
                continue
        if getattr(aerodrome, attr) != value:
            setattr(aerodrome, attr, value)
            written += 1
    return written


def _write_runways(session: Session, aerodrome: Aerodrome, rows: list[dict]) -> int:
    if not rows:
        return 0
    session.execute(delete(Runway).where(Runway.aerodrome_icao == aerodrome.icao))
    session.flush()
    airac = aerodrome.source_airac_cycle
    for row in rows:
        session.add(Runway(
            aerodrome_icao=aerodrome.icao,
            source_airac_cycle=airac,
            **row,
        ))
    return len(rows)


def _write_frequencies(session: Session, aerodrome: Aerodrome, rows: list[dict]) -> int:
    if not rows:
        return 0
    session.execute(delete(Frequency).where(Frequency.aerodrome_icao == aerodrome.icao))
    session.flush()
    airac = aerodrome.source_airac_cycle
    for row in rows:
        session.add(Frequency(
            aerodrome_icao=aerodrome.icao,
            source_airac_cycle=airac,
            **row,
        ))
    return len(rows)


# ---------------------------------------------------------------------------
# Enum mappers (unchanged from #35)
# ---------------------------------------------------------------------------

def _map_surface(raw: str | None) -> RunwaySurface:
    if not raw:
        return RunwaySurface.OTHER
    token = str(raw).strip().lower()
    for surf in RunwaySurface:
        if surf.value == token:
            return surf
    if "asph" in token or "bitum" in token:
        return RunwaySurface.ASPHALT
    if "beton" in token or "conc" in token:
        return RunwaySurface.CONCRETE
    if "gras" in token or "grass" in token:
        return RunwaySurface.GRASS
    if "gravel" in token or "schotter" in token:
        return RunwaySurface.GRAVEL
    return RunwaySurface.OTHER


def _map_freq_type(token: str) -> FrequencyType | None:
    token = token.strip().lower()
    for ft in FrequencyType:
        if ft.value == token:
            return ft
    alias = {
        "tower": FrequencyType.TWR,
        "ground": FrequencyType.GND,
        "approach": FrequencyType.APP,
        "departure": FrequencyType.DEP,
        "delivery": FrequencyType.DEL,
        "information": FrequencyType.INFO,
    }
    return alias.get(token)
