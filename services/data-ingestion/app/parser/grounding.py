"""Grounding check — verifies LLM values are LITERALLY present in the image.

After the consensus engine has picked a value based on 2-of-2 LLM agreement,
this module runs a deterministic, non-LLM check against the source image:

    1. Crop the PNG to the bbox reported by the LLM
    2. Run Tesseract OCR on that crop
    3. Require the claimed value (as a sequence of characters / digits) to
       appear in the OCR text

If grounding fails, the value is REJECTED regardless of how confidently the
LLMs agreed — this catches correlated memory-based hallucinations where
both LLMs "remember" a famous airport fact from training data instead of
reading the chart in front of them.

The check is deliberately conservative:
 - Alphanumeric comparison only (punctuation and whitespace stripped)
 - Case-insensitive
 - Unicode NFC-normalised
 - Skips fields that are printed in a fundamentally different form than
   how they are stored (coordinates: printed as DMS, stored as decimal)

This module does NO extraction — it only verifies existing claims.
"""

from __future__ import annotations

import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BBox = tuple[int, int, int, int]


# Fields whose stored form does not match the printed form — grounding is
# meaningless for these and we skip instead of doing a bogus check.
SKIP_GROUNDING_FIELDS = frozenset({
    "latitude",      # stored decimal, printed DMS
    "longitude",     # same
    "true_heading",  # may be printed as magnetic+deg or with °-suffix only
})


@dataclass
class GroundingResult:
    """Outcome of a single grounding attempt."""

    field: str
    claimed_value: Any
    bbox: BBox | None
    grounded: bool
    reason: str
    ocr_text: str | None = None


class TesseractNotInstalled(RuntimeError):
    """Raised once per process if the tesseract binary is missing."""


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def ensure_tesseract() -> None:
    if not tesseract_available():
        raise TesseractNotInstalled(
            "`tesseract` binary not found. Install in the data-ingestion "
            "Dockerfile: `apt-get install -y tesseract-ocr tesseract-ocr-deu "
            "tesseract-ocr-eng`."
        )


def _strip_for_grounding(text: str) -> str:
    """Lowercase + NFC + keep only alphanumeric characters."""
    t = unicodedata.normalize("NFC", text)
    return "".join(c for c in t if c.isalnum()).lower()


def value_present_in_text(claimed_value: Any, ocr_text: str) -> bool:
    if claimed_value is None:
        return False
    claim = _strip_for_grounding(str(claimed_value))
    ocr = _strip_for_grounding(ocr_text)
    return bool(claim) and (claim in ocr)


def _crop_image(image_path: Path, bbox: BBox) -> bytes:
    """Return PNG bytes of the cropped region. Uses Pillow if available."""
    from PIL import Image   # optional import; Pillow is in requirements.txt

    x0, y0, x1, y1 = bbox
    with Image.open(image_path) as img:
        width, height = img.size
        # Sanitize bbox to image bounds — reject bbox fully outside.
        x0 = max(0, min(int(x0), width))
        y0 = max(0, min(int(y0), height))
        x1 = max(0, min(int(x1), width))
        y1 = max(0, min(int(y1), height))
        if x1 <= x0 or y1 <= y0:
            raise ValueError(f"bbox {bbox!r} empty after clamping to {width}x{height}")
        crop = img.crop((x0, y0, x1, y1))
        import io
        buf = io.BytesIO()
        crop.save(buf, format="PNG")
        return buf.getvalue()


def _ocr_png_bytes(png_bytes: bytes, lang: str = "deu+eng") -> str:
    """Run tesseract against PNG bytes, return raw text."""
    ensure_tesseract()
    # Using --psm 6 (single uniform block) is appropriate for small table-cell crops.
    proc = subprocess.run(
        ["tesseract", "stdin", "stdout", "-l", lang, "--psm", "6"],
        input=png_bytes,
        capture_output=True,
        timeout=20,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"tesseract failed (rc={proc.returncode}): {proc.stderr.decode('utf-8', 'replace')}"
        )
    return proc.stdout.decode("utf-8", "replace")


def ground(
    *,
    field: str,
    claimed_value: Any,
    image_path: Path,
    bbox: BBox | None,
) -> GroundingResult:
    """Attempt to ground a single claimed value.

    Returns a GroundingResult describing the outcome. Never raises for
    expected failure modes (missing bbox, OCR disagreement) — only for
    environmental failures (Pillow missing, tesseract missing).
    """
    if field in SKIP_GROUNDING_FIELDS:
        return GroundingResult(
            field=field,
            claimed_value=claimed_value,
            bbox=bbox,
            grounded=True,
            reason="grounding_skipped_by_field_policy",
        )

    if claimed_value is None:
        return GroundingResult(
            field=field,
            claimed_value=None,
            bbox=bbox,
            grounded=False,
            reason="no_claimed_value",
        )

    if bbox is None:
        return GroundingResult(
            field=field,
            claimed_value=claimed_value,
            bbox=None,
            grounded=False,
            reason="no_bbox_from_llm",
        )

    try:
        crop = _crop_image(image_path, bbox)
    except Exception as exc:  # noqa: BLE001
        return GroundingResult(
            field=field,
            claimed_value=claimed_value,
            bbox=bbox,
            grounded=False,
            reason=f"crop_failed: {type(exc).__name__}: {exc}",
        )

    try:
        ocr = _ocr_png_bytes(crop)
    except TesseractNotInstalled:
        raise  # environmental — caller must decide whether to skip or fail
    except Exception as exc:  # noqa: BLE001
        return GroundingResult(
            field=field,
            claimed_value=claimed_value,
            bbox=bbox,
            grounded=False,
            reason=f"ocr_failed: {type(exc).__name__}: {exc}",
        )

    if value_present_in_text(claimed_value, ocr):
        return GroundingResult(
            field=field,
            claimed_value=claimed_value,
            bbox=bbox,
            grounded=True,
            reason="value_substring_found_in_ocr",
            ocr_text=ocr,
        )
    return GroundingResult(
        field=field,
        claimed_value=claimed_value,
        bbox=bbox,
        grounded=False,
        reason="value_not_present_in_ocr",
        ocr_text=ocr,
    )


def ground_any(
    *,
    field: str,
    claimed_value: Any,
    image_path: Path,
    bboxes: list[BBox],
) -> GroundingResult:
    """Attempt grounding across multiple bboxes. Accept if ANY passes.

    Used when both Claude and OpenAI reported (possibly slightly different)
    bboxes for the same value. Either confirming is sufficient evidence
    that the value was read rather than recalled.
    """
    last: GroundingResult | None = None
    for bbox in bboxes:
        result = ground(
            field=field,
            claimed_value=claimed_value,
            image_path=image_path,
            bbox=bbox,
        )
        if result.grounded:
            return result
        last = result
    return last or GroundingResult(
        field=field,
        claimed_value=claimed_value,
        bbox=None,
        grounded=False,
        reason="no_bboxes_provided",
    )
