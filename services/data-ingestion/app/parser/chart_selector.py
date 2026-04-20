"""Pick the best chart PNG for a requested field group.

The DFS scraper captured multiple PNGs per aerodrome and there is no
deterministic naming convention telling us which page contains which
AIP section. Calling two LLM providers on every page would be wasteful.

Strategy
--------

Tesseract-OCR the full image (cheap, free, local). Count occurrences of
aviation keywords associated with each AIP sub-section. Score each
candidate image and return them in ranked order.

Keywords are deliberately over-specified; even if one keyword triggers
false-positively on an unrelated page, the requirement for 3+ hits
keeps noise down. The scoring is only a hint — the actual LLM
extraction still has to produce a plausible value that survives 2-of-2
consensus + grounding.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

log = logging.getLogger(__name__)

FieldGroup = Literal["geo", "runways", "frequencies"]


# Weighted keywords per field group. Each tuple is (keyword, weight).
# Strong anchors ("AD 2.2", TORA/TODA/ASDA/LDA, AD 2.18) score ≥ 3 on their own.
# Regular keywords score 1. Upper-case so matching is trivial.
KEYWORDS: dict[FieldGroup, tuple[tuple[str, int], ...]] = {
    "geo": (
        ("AD 2.2", 3),
        ("ARP", 2), ("AERODROME REFERENCE POINT", 3),
        ("ELEV", 1), ("ELEVATION", 1),
        ("LATITUDE", 2), ("LONGITUDE", 2),
        ("MAG VAR", 2), ("MAGNETIC VARIATION", 2), ("MISSWEISUNG", 2),
        ("OPERATOR", 1), ("BETREIBER", 1),
        ("REFERENCE TEMP", 2),
    ),
    "runways": (
        ("AD 2.12", 3), ("AD 2.13", 3),
        ("TORA", 3), ("TODA", 3), ("ASDA", 3), ("LDA", 2),
        ("DESIGNATOR", 2), ("KENNUNG", 2),
        ("RWY", 1), ("RUNWAY", 1), ("PISTE", 1),
        ("SURFACE", 1), ("OBERFLÄCHE", 1), ("OBERFLACHE", 1),
        ("ASPHALT", 1), ("CONCRETE", 1), ("BETON", 1), ("GRASS", 1), ("GRAS", 1),
        ("ILS", 1),
    ),
    "frequencies": (
        ("AD 2.18", 3),
        ("ATS COMMUNICATION", 3),
        ("TWR", 1), ("TOWER", 1), ("TURM", 1),
        ("GND", 1), ("GROUND", 1), ("BODEN", 1),
        ("ATIS", 1),
        ("APP", 1), ("APPROACH", 1), ("ANFLUG", 1),
        ("DEL", 1), ("DELIVERY", 1),
        ("FREQ", 1), ("FREQUENCY", 1), ("FREQUENZ", 1),
        ("MHZ", 1),
    ),
}

# Minimum total weight for a page to be considered a plausible candidate.
MIN_SCORE = 3


@dataclass
class ChartCandidate:
    path: Path
    score: int
    hits: list[str]


def _ocr_full_image(image: Path, *, psm: int = 3, lang: str = "deu+eng", timeout: int = 30) -> str:
    """Fast Tesseract pass for keyword scanning."""
    try:
        proc = subprocess.run(
            ["tesseract", str(image), "stdout", "-l", lang, "--psm", str(psm)],
            capture_output=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            log.warning("tesseract failed on %s: %s", image.name, proc.stderr.decode("utf-8", "replace"))
            return ""
        return proc.stdout.decode("utf-8", "replace").upper()
    except subprocess.TimeoutExpired:
        log.warning("tesseract timeout on %s", image.name)
        return ""


def rank_charts(aerodrome_dir: Path, *, field_group: FieldGroup) -> list[ChartCandidate]:
    """Return candidate charts ranked by keyword-hit score, best first.

    Only print-variant PNGs are considered (the print version has the
    full-resolution text; previews are subscaled and OCR-unfriendly).
    """
    if not aerodrome_dir.is_dir():
        return []

    weighted_kws = KEYWORDS[field_group]
    candidates: list[ChartCandidate] = []

    for png in sorted(aerodrome_dir.glob("*_print.png")):
        text = _ocr_full_image(png)
        if not text:
            continue
        hits: list[str] = []
        score = 0
        for kw, weight in weighted_kws:
            if kw in text:
                hits.append(kw)
                score += weight
        if score >= MIN_SCORE:
            candidates.append(
                ChartCandidate(path=png, score=score, hits=sorted(set(hits)))
            )

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def pick_chart(aerodrome_dir: Path, *, field_group: FieldGroup) -> ChartCandidate | None:
    """Return the single best candidate, or None if no page qualifies."""
    ranked = rank_charts(aerodrome_dir, field_group=field_group)
    return ranked[0] if ranked else None
