"""Static-file endpoint for scraped aerodrome chart PNGs.

Serves files from /app/data/aerodromes/<ICAO>/<filename> — the read-only
volume mount populated by the DFS scraper. Path-traversal is prevented by
resolving the requested path and verifying it still lives inside the
aerodrome-specific directory.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/charts", tags=["charts"])

_DATA_ROOT = Path("/app/data/aerodromes")
_CACHE_SECONDS = 86_400  # AIRAC cycle is month-long; one day is conservative.

_ICAO_RE = re.compile(r"^[A-Z]{4}$")
_FILENAME_RE = re.compile(r"^[A-Za-z0-9_\-]+\.(png|jpg|jpeg)$")


@router.get("/{icao}/{filename}", response_class=FileResponse)
def get_chart_file(icao: str, filename: str) -> FileResponse:
    icao_upper = icao.upper()
    if not _ICAO_RE.match(icao_upper):
        raise HTTPException(status_code=400, detail="ICAO must be four uppercase letters")
    if not _FILENAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    aerodrome_dir = (_DATA_ROOT / icao_upper).resolve()
    requested = (aerodrome_dir / filename).resolve()

    # Guard against path traversal: requested must be inside aerodrome_dir.
    try:
        requested.relative_to(aerodrome_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid chart path") from exc

    if not requested.is_file():
        raise HTTPException(status_code=404, detail="Chart file not found")

    return FileResponse(
        requested,
        media_type="image/png",
        headers={"Cache-Control": f"public, max-age={_CACHE_SECONDS}"},
    )
