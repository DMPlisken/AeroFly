"""Image-size guard for vision provider calls.

User-chosen strategy (per #28): send PNGs to Claude/OpenAI exactly as
stored on disk. Fidelity is preserved by default. Only when the
provider returns a size-related error do we downscale in memory and
retry once.

Revised for #36 diagnosis: Anthropic has TWO independent limits —
pixel dimensions (~8 MP) AND base64 body size (5 MB). A chart that's
fine on pixels can still exceed the byte limit after PNG re-encode
because PNG is lossless and high-detail aerodrome charts compress
poorly. The downscaler now walks a ladder of resolutions until either

  - the re-encoded PNG fits under an empirical byte budget, or
  - it has been shrunk to the smallest useful size (768 px long edge)

Below 768 px the LLMs genuinely lose legibility of small type, so we
stop there and let the provider error propagate.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass

from PIL import Image

log = logging.getLogger(__name__)

# Anthropic rejects images whose BASE64 body exceeds 5 MB. A raw PNG of
# ~3.7 MB expands to ~5 MB base64. Leave headroom for JSON overhead.
DEFAULT_MAX_BYTES = 3_600_000

# Back-compat shim for imports that predate the byte-budget ladder.
# Tests and callers may still reference this as the pixel cap.
DEFAULT_MAX_LONG_EDGE = 2048

# Ladder of pixel dimensions tried from largest to smallest. Stops early
# once the PNG fits under the byte budget.
_DOWNSCALE_LADDER: tuple[int, ...] = (2048, 1568, 1280, 1024, 768)

# Substrings that strongly suggest the error is about the image being
# too large. We require BOTH the word "image" AND one of these hints so
# random BadRequestErrors about prompts, tokens, or formatting don't
# trigger a waste-of-money resample.
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
    "5 mb",
    "5mb",
    "bytes >",
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


def _resize_and_encode(img: Image.Image, long_edge: int) -> tuple[bytes, tuple[int, int]]:
    """Resize to `long_edge` preserving aspect, re-encode PNG, return bytes + new dims."""
    w, h = img.size
    ratio = long_edge / max(w, h)
    new_w = max(1, int(w * ratio))
    new_h = max(1, int(h * ratio))
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    if resized.mode not in ("RGB", "RGBA", "L", "LA"):
        resized = resized.convert("RGBA" if "A" in resized.mode else "RGB")
    buf = io.BytesIO()
    resized.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), (new_w, new_h)


def downscale_png(
    png_bytes: bytes,
    *,
    max_long_edge: int | None = None,  # legacy kw; ignored if set — ladder drives now
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> DownscaleResult:
    """Walk a pixel-ladder until the re-encoded PNG fits under max_bytes.

    The legacy `max_long_edge` parameter is preserved for backward-compat
    with the unit tests (they cap the ladder's top step). Any value > 768
    is folded into the ladder; values ≤ 768 force that as the sole step.
    """
    img = Image.open(io.BytesIO(png_bytes))
    original_size = img.size

    # Already within byte budget AND not forced-shrunk by a legacy kw? short-circuit.
    if len(png_bytes) <= max_bytes and max_long_edge is None:
        if max(original_size) <= _DOWNSCALE_LADDER[0]:
            return DownscaleResult(
                png_bytes=png_bytes,
                original_size=original_size,
                new_size=None,
            )

    # Build the ladder for this call.
    if max_long_edge is not None:
        # Respect the caller's cap. Use ladder steps that are ≤ cap,
        # including the cap itself as the first entry. Collapse to just
        # the cap if it's below the smallest standard step.
        cap = max(1, int(max_long_edge))
        if cap < _DOWNSCALE_LADDER[-1]:
            ladder = (cap,)
        else:
            ladder = (cap,) + tuple(s for s in _DOWNSCALE_LADDER if s < cap)
        # If the original already fits cap AND byte budget, no-op.
        if max(original_size) <= cap and len(png_bytes) <= max_bytes:
            return DownscaleResult(
                png_bytes=png_bytes,
                original_size=original_size,
                new_size=None,
            )
    else:
        ladder = _DOWNSCALE_LADDER

    last_bytes: bytes | None = None
    last_dims: tuple[int, int] | None = None
    for step in ladder:
        if max(original_size) <= step and len(png_bytes) <= max_bytes:
            # Original already fits this step AND byte budget — return as-is.
            return DownscaleResult(
                png_bytes=png_bytes,
                original_size=original_size,
                new_size=None,
            )
        new_bytes, new_dims = _resize_and_encode(img, step)
        last_bytes, last_dims = new_bytes, new_dims
        log.info(
            "image_guard: %dx%d -> %dx%d (%d -> %d bytes, budget %d)",
            original_size[0], original_size[1],
            new_dims[0], new_dims[1],
            len(png_bytes), len(new_bytes), max_bytes,
        )
        if len(new_bytes) <= max_bytes:
            return DownscaleResult(
                png_bytes=new_bytes,
                original_size=original_size,
                new_size=new_dims,
            )

    # Exhausted the ladder without fitting the byte budget. Return the
    # smallest rendering we produced — better than nothing; the caller's
    # retry will pass this to the API and either succeed or fail-closed.
    return DownscaleResult(
        png_bytes=last_bytes or png_bytes,
        original_size=original_size,
        new_size=last_dims,
    )
