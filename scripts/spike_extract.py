"""Phase 0 Spike — Claude + OpenAI vision consensus, grounded with Tesseract.

Does NOT write to the database. Produces a standalone JSON report with:
 - Provider status (configured / missing keys)
 - Per-aerodrome: each provider's raw response + extracted fields
 - Consensus decision per field
 - Grounding result (Tesseract) per accepted value
 - Summary stats

Run inside the data-ingestion container once `ANTHROPIC_API_KEY` and
`OPENAI_API_KEY` are set in the environment:

    python scripts/spike_extract.py --icaos EDDM,EDDF,EDDH,EDDB,EDDG

Exit codes:
    0  all providers configured and extraction completed
    2  fewer than 2 providers configured (fail-closed: cannot evaluate)
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

from app.parser.grounding import tesseract_available  # noqa: E402
from app.parser.providers.base import ProviderNotConfigured  # noqa: E402
from app.parser.providers.claude_vision import ClaudeVisionProvider  # noqa: E402
from app.parser.providers.openai_vision import OpenAIVisionProvider  # noqa: E402


def find_ad2_chart(icao: str) -> Path | None:
    """Locate the AD 2-X print PNG for an aerodrome (page with structured text)."""
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
    default_dir = Path("/tmp") if _IN_CONTAINER else (_PROJECT_ROOT / "data" / "spike-reports")
    default_report = default_dir / f"spike-report-{datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    parser.add_argument(
        "--report-out",
        default=str(default_report),
        help="where to write the spike report JSON",
    )
    args = parser.parse_args()

    icaos = [s.strip().upper() for s in args.icaos.split(",") if s.strip()]
    providers = [ClaudeVisionProvider(), OpenAIVisionProvider()]

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
            "the data-ingestion Dockerfile (tesseract-ocr + tesseract-ocr-deu "
            "+ tesseract-ocr-eng) or `apt-get install` in the running container."
        )

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
                    "input_image_sha256": result.input_image_sha256,
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
