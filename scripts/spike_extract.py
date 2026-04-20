"""Phase 0 Spike — Claude + OpenAI vision consensus on VFR charts.

Does NOT write to the database. Produces a standalone JSON report with:
 - Provider status (configured / missing keys)
 - Per-aerodrome × field_group: ranked candidate charts, per-provider output
 - First-candidate-that-produced-data, cascading through candidates
 - Summary stats

Chart selection is manifest-driven (#30 tags) — Tesseract keyword
scoring is gone. For each field_group the selector returns all
acceptable charts in ranked order; this script iterates them until one
produces at least one non-null field from both providers (cascade).

Run inside the data-ingestion container once `ANTHROPIC_API_KEY` and
`OPENAI_API_KEY` are set in the environment:

    python scripts/spike_extract.py --icaos EDDM,EDDF,EDDH

Exit codes:
    0  all providers configured and extraction completed
    2  fewer than 2 providers configured (fail-closed: cannot evaluate)
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
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
    _DATA_ROOT = _PROJECT_ROOT / "data" / "aerodromes"

from app.core.config import settings  # noqa: E402
from app.db import get_session_factory  # noqa: E402
from app.parser.chart_selector import rank_charts  # noqa: E402
from app.parser.grounding import tesseract_available  # noqa: E402
from app.parser.providers.base import FieldGroup, ProviderNotConfigured  # noqa: E402
from app.parser.providers.claude_vision import ClaudeVisionProvider  # noqa: E402
from app.parser.providers.openai_vision import OpenAIVisionProvider  # noqa: E402
from app.parser.usage_tracker import UsageTracker  # noqa: E402

# Max candidates to try per field_group before giving up. Keeps the
# cost bounded even on airports with many charts (EDDH has 8).
MAX_CANDIDATES_PER_GROUP = 3

# Field groups this spike covers. Matches the expanded VFR scope (#32).
FIELD_GROUPS: tuple[FieldGroup, ...] = (
    "geo",
    "runways",
    "frequencies",
    "obstacles",
    "reporting_points",
)


def _has_any_signal(parsed) -> bool:
    """Cheap check: did the provider extract anything non-null?

    Recurses shallowly. A response with all-null fields is fail-closed
    behaviour (the LLM couldn't read anything) and we should try the
    next candidate in the cascade.
    """
    if parsed is None:
        return False
    if isinstance(parsed, dict):
        for v in parsed.values():
            if _has_any_signal(v):
                return True
        return False
    if isinstance(parsed, list):
        return any(_has_any_signal(item) for item in parsed)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--icaos",
        default="EDDM,EDDF",
        help="comma-separated ICAO list (default: EDDM,EDDF)",
    )
    default_dir = Path("/tmp") if _IN_CONTAINER else (_PROJECT_ROOT / "data" / "spike-reports")
    default_report = default_dir / f"spike-report-{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    parser.add_argument(
        "--report-out",
        default=str(default_report),
        help="where to write the spike report JSON",
    )
    args = parser.parse_args()

    icaos = [s.strip().upper() for s in args.icaos.split(",") if s.strip()]
    session_factory = get_session_factory(settings.database_url)
    tracker = UsageTracker(session_factory)
    providers = [
        ClaudeVisionProvider(tracker=tracker),
        OpenAIVisionProvider(tracker=tracker),
    ]

    provider_status = {
        p.name: "CONFIGURED" if p.is_configured() else "MISSING_CREDENTIALS"
        for p in providers
    }
    ground_available = tesseract_available()

    print("=== Provider status ===")
    for name, state in provider_status.items():
        mark = "OK " if state == "CONFIGURED" else "-- "
        print(f"  {mark} {name}: {state}")
    print(f"  {'OK ' if ground_available else '-- '} tesseract (grounding): "
          f"{'installed' if ground_available else 'MISSING_BINARY'}")
    print()

    report: dict = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "icaos": icaos,
        "providers": provider_status,
        "tesseract_available": ground_available,
        "results": [],
        "limitations": [],
    }

    configured = [p for p in providers if p.is_configured()]
    if len(configured) < 2:
        report["limitations"].append(
            "Fewer than 2 providers configured — 2-of-2 consensus cannot be "
            "evaluated. Set ANTHROPIC_API_KEY and OPENAI_API_KEY, then re-run."
        )
        _write_report(args.report_out, report)
        print("Not enough providers configured. Report:", args.report_out)
        return 2

    if not ground_available:
        report["limitations"].append(
            "Tesseract binary missing — grounding check skipped. Install via "
            "the data-ingestion Dockerfile or `apt-get install` in the container."
        )

    for icao in icaos:
        icao_block: dict = {"icao": icao, "field_groups": {}}
        aerodrome_dir = _DATA_ROOT / icao

        for field_group in FIELD_GROUPS:
            candidates = rank_charts(aerodrome_dir, field_group=field_group)
            group_block: dict = {
                "candidates_considered": [
                    {
                        "name": c.path.name,
                        "chart_type": c.chart_type,
                        "chart_suffix": c.chart_suffix,
                    }
                    for c in candidates[:MAX_CANDIDATES_PER_GROUP]
                ],
                "accepted_chart": None,
                "providers": {},
            }
            if not candidates:
                group_block["error"] = "no chart matched the field group's accepted chart_types"
                icao_block["field_groups"][field_group] = group_block
                continue

            # Cascade: try each candidate until one produces non-null output
            # from ALL providers (we want both sources to have something
            # before we consider the candidate "accepted"). Fallback: if
            # exhausted without consensus, record the last attempt.
            accepted = None
            for candidate in candidates[:MAX_CANDIDATES_PER_GROUP]:
                attempt: dict[str, dict] = {}
                for p in configured:
                    try:
                        result = p.extract(
                            image_path=candidate.path,
                            field_group=field_group,
                            aerodrome_icao=icao,
                        )
                        attempt[p.name] = {
                            "model_version": result.model_version,
                            "prompt_version": result.prompt_version,
                            "input_image_sha256": result.input_image_sha256,
                            "raw": result.raw_response,
                            "has_signal": _has_any_signal(result.raw_response.get("parsed")),
                        }
                    except ProviderNotConfigured as exc:
                        attempt[p.name] = {"error": f"not configured: {exc}"}
                    except Exception as exc:  # noqa: BLE001
                        attempt[p.name] = {
                            "error": f"{type(exc).__name__}: {str(exc)[:200]}"
                        }

                all_have_signal = all(
                    entry.get("has_signal") is True for entry in attempt.values()
                )
                if all_have_signal:
                    accepted = candidate
                    group_block["accepted_chart"] = candidate.path.name
                    group_block["providers"] = attempt
                    break
                # Store last attempt for diagnosis even if we cascade further.
                group_block["providers"] = attempt

            if accepted is None:
                group_block["error"] = (
                    f"no candidate in top {MAX_CANDIDATES_PER_GROUP} produced "
                    "non-null output from both providers"
                )

            icao_block["field_groups"][field_group] = group_block

        report["results"].append(icao_block)

    _write_report(args.report_out, report)
    print(f"Spike report written to {args.report_out}")
    return 0


def _write_report(path_str: str, report: dict) -> None:
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
