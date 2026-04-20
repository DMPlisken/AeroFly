"""Diagnostic — call Claude + OpenAI directly on EDDF charts.

Prints the FULL parsed JSON per provider per chart per field_group so
we can see why consensus is failing (one provider sees, other doesn't?
both see but disagree? prompt filters out?).

Run inside the data-ingestion container:
    docker compose exec -T data-ingestion python scripts/diagnose_eddf.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/app")

from app.parser.providers.claude_vision import ClaudeVisionProvider  # noqa: E402
from app.parser.providers.openai_vision import OpenAIVisionProvider  # noqa: E402

DATA_ROOT = Path("/app/data/aerodromes/EDDF")

CHARTS = [
    "EDDF_Frankfurt_Main_1_print.png",
    "EDDF_Frankfurt_Main_2_print.png",
    "EDDF_Frankfurt_Main_3_print.png",
    "EDDF_Frankfurt_Main_5_print.png",
    "EDDF_Frankfurt_Main_Terminal_Chart_print.png",
]

FIELD_GROUPS = ["runways", "frequencies"]


def _walk_values(parsed, prefix=""):
    """Yield every non-null ExtractedValue as a (path, value) tuple."""
    if parsed is None:
        return
    if isinstance(parsed, dict):
        if "value" in parsed:
            if parsed.get("value") is not None:
                yield prefix, parsed["value"]
            return
        for k, v in parsed.items():
            yield from _walk_values(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(parsed, list):
        for i, item in enumerate(parsed):
            yield from _walk_values(item, f"{prefix}[{i}]")


def main():
    claude = ClaudeVisionProvider()
    openai = OpenAIVisionProvider()
    if not (claude.is_configured() and openai.is_configured()):
        print("Missing API keys")
        return 2

    for field_group in FIELD_GROUPS:
        print(f"\n{'=' * 70}")
        print(f"FIELD GROUP: {field_group}")
        print(f"{'=' * 70}")
        for chart_name in CHARTS:
            chart_path = DATA_ROOT / chart_name
            if not chart_path.exists():
                print(f"\n--- {chart_name} — FILE MISSING")
                continue
            print(f"\n--- {chart_name} ---")
            for p, label in ((claude, "CLAUDE"), (openai, "OPENAI")):
                try:
                    res = p.extract(
                        image_path=chart_path,
                        field_group=field_group,
                        aerodrome_icao="EDDF",
                    )
                    parsed = res.raw_response.get("parsed")
                    vals = list(_walk_values(parsed))
                    print(f"  {label}: {len(vals)} non-null values")
                    for path, val in vals[:20]:
                        s = str(val)[:60]
                        print(f"    {path} = {s}")
                except Exception as exc:
                    print(f"  {label}: {type(exc).__name__}: {str(exc)[:200]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
