"""Image-size guard for vision provider calls.

User-chosen strategy: send PNGs to Claude/OpenAI exactly as stored on
disk. Fidelity is preserved by default. Only when the provider returns a
size-related error do we downscale the image in memory and retry once.

Why this shape

- Preflight downscale would penalise every call, including ones that
  would have worked fine at full resolution.
- Claude Sonnet 4.6 vision rejects PNGs over ~8 MP (or ~5 MB base64) with
  a BadRequestError; GPT-4o silently downscales but re-encodes at lower
  quality. Both share the same fallback: send smaller, try again.
- One retry only. If the retry still fails for any reason, the caller's
  existing fail-closed path handles it — the pipeline never guesses.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from PIL import Image

log = logging.getLogger(__name__)

DEFAULT_MAX_LONG_EDGE = 2048

# Substrings that strongly suggest the error is about the image being too
# large. We intentionally require BOTH the word "image" AND one of the
# hints — random BadRequestErrors about prompts, tokens, or formatting
# must NOT trigger a downscale retry.
_IMAGE_SIZE_HINTS = (
    "too large",
    "too big",
    "exceeds",
    "maximum",
    "too many pixels",
    "dimensions",
    "megapixel",
    "pixel",
    "image_size_exceeded",
    "size limit",
)


@dataclass
class DownscaleResult:
    png_bytes: bytes
    original_size: tuple[int, int]
    new_size: tuple[int, int] | None  # None when no downscale was needed


def is_image_size_error(exc: BaseException) -> bool:
    """Heuristic: does this exception look like a provider-side size rejection?

    Checked against the stringified exception. Requires both ``image`` and
    at least one size-related hint. Conservative on purpose — a false
    positive would waste a resample; a false negative simply propagates
    the original error as today.
    """
    msg = str(exc).lower()
    if "image" not in msg:
        return False
    return any(hint in msg for hint in _IMAGE_SIZE_HINTS)


def downscale_png(
    png_bytes: bytes,
    *,
    max_long_edge: int = DEFAULT_MAX_LONG_EDGE,
) -> DownscaleResult:
    """Resize a PNG so its longest edge fits ``max_long_edge`` pixels.

    Preserves aspect ratio. Uses LANCZOS for quality. If the image is
    already within bounds, returns the original bytes unchanged and
    ``new_size=None`` so the caller can short-circuit.
    """
    img = Image.open(io.BytesIO(png_bytes))
    width, height = img.size
    long_edge = max(width, height)

    if long_edge <= max_long_edge:
        return DownscaleResult(
            png_bytes=png_bytes,
            original_size=(width, height),
            new_size=None,
        )

    ratio = max_long_edge / long_edge
    new_width = max(1, int(width * ratio))
    new_height = max(1, int(height * ratio))

    resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Normalise mode to RGB(A) for reliable PNG re-encoding; input may be P/L/etc.
    if resized.mode not in ("RGB", "RGBA", "L", "LA"):
        resized = resized.convert("RGBA" if "A" in resized.mode else "RGB")

    buf = io.BytesIO()
    resized.save(buf, format="PNG", optimize=True)

    log.info(
        "image_guard: downscaled %dx%d -> %dx%d (%d -> %d bytes)",
        width, height, new_width, new_height,
        len(png_bytes), buf.tell(),
    )

    return DownscaleResult(
        png_bytes=buf.getvalue(),
        original_size=(width, height),
        new_size=(new_width, new_height),
    )
