"""Phase 0 Spike — orchestrates a multi-source extraction on a few aerodromes.

This script does NOT write to the database. It produces a standalone JSON
report under `data/spike-reports/<date>.json` plus prints a terminal summary.

Run (inside data-ingestion container with ANTHROPIC_API_KEY + OPENAI_API_KEY
set in the environment):

    python scripts/spike_extract.py --icaos EDDM,EDDF,EDDH,EDDB,EDDG

Status: scaffolding only. The actual provider calls are deferred until
Gate α — each provider raises NotImplementedError on call. Once API keys
are available, enabling the calls is local to `parser/providers/*.py`.
"""

from __future__ import annotations

import argparse
import json
import os
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

from app.parser.providers.base import ProviderNotConfigured  # noqa: E402
from app.parser.providers.claude_vision import ClaudeVisionProvider  # noqa: E402
from app.parser.providers.openai_vision import OpenAIVisionProvider  # noqa: E402
from app.parser.providers.tesseract import TesseractProvider  # noqa: E402


def find_ad2_chart(icao: str) -> Path | None:
    """Locate the AD 2-X print PNG for an aerodrome (the page with structured text)."""
    aerodrome_dir = _DATA_ROOT / icao.upper()
    if not aerodrome_dir.exists():
        return None
    candidates = sorted(aerodrome_dir.glob("AD_2-*_print.png"))
    return candidates[0] if candidates else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--icaos",
        default="EDDM,EDDF",
        help="comma-separated ICAO list (default: EDDM,EDDF)",
    )
    # /app/data is mounted read-only inside the container — spike reports go to
    # a writable location by default.
    default_dir = Path("/tmp") if _IN_CONTAINER else (_PROJECT_ROOT / "data" / "spike-reports")
    default_report = default_dir / f"spike-report-{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    parser.add_argument(
        "--report-out",
        default=str(default_report),
        help="where to write the spike report JSON",
    )
    args = parser.parse_args()

    icaos = [s.strip().upper() for s in args.icaos.split(",") if s.strip()]
    providers = [
        ClaudeVisionProvider(),
        OpenAIVisionProvider(),
        TesseractProvider(),
    ]

    # Report which providers are configured so the reader knows what the spike
    # actually tested vs what was missing.
    provider_status = {
        p.name: "CONFIGURED" if p.is_configured() else "MISSING_CREDENTIALS"
        for p in providers
    }
    print("=== Provider status ===")
    for name, state in provider_status.items():
        mark = "OK " if state == "CONFIGURED" else "-- "
        print(f"  {mark} {name}: {state}")
    print()

    report: dict = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "icaos": icaos,
        "providers": provider_status,
        "results": [],
        "limitations": [],
    }

    # Hard-stop: if fewer than 2 providers are available the spike cannot
    # even demonstrate the consensus logic. Print a clear message and exit.
    configured = [p for p in providers if p.is_configured()]
    if len(configured) < 2:
        report["limitations"].append(
            "Fewer than 2 providers configured — consensus cannot be evaluated. "
            "Set ANTHROPIC_API_KEY and OPENAI_API_KEY, and ensure tesseract-ocr "
            "is installed, before running the real spike."
        )
        _write_report(args.report_out, report)
        print("Not enough providers configured. Report:", args.report_out)
        return 2

    for icao in icaos:
        image = find_ad2_chart(icao)
        if image is None:
            report["results"].append({"icao": icao, "error": "no AD 2-X PNG in data/"})
            continue

        icao_block: dict = {"icao": icao, "image": str(image), "providers": {}}
        for p in configured:
            try:
                result = p.extract(image_path=image, field_group="geo")
                icao_block["providers"][p.name] = {
                    "model_version": result.model_version,
                    "prompt_version": result.prompt_version,
                    "raw": result.raw_response,
                }
            except ProviderNotConfigured as exc:
                icao_block["providers"][p.name] = {"error": f"not configured: {exc}"}
            except NotImplementedError as exc:
                icao_block["providers"][p.name] = {"deferred": str(exc)}
            except Exception as exc:  # noqa: BLE001
                icao_block["providers"][p.name] = {
                    "error": f"{type(exc).__name__}: {exc}"
                }
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
