"""Unit tests for the image-size guard."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.parser.image_guard import (
    DEFAULT_MAX_LONG_EDGE,
    downscale_png,
    is_image_size_error,
)


def _make_png(width: int, height: int, *, color: tuple[int, int, int] = (128, 128, 128)) -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# is_image_size_error — heuristic detector
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "message",
    [
        "image too large: 8000x8000 pixels exceeds maximum",
        "Bad request: image dimensions too big",
        "image exceeds 1568x1568 pixels",
        "Image size limit exceeded: 5MB",
        "too many megapixels in image",
        "image_size_exceeded",
    ],
)
def test_is_image_size_error_true(message: str):
    assert is_image_size_error(ValueError(message)) is True


@pytest.mark.parametrize(
    "message",
    [
        "Invalid API key",
        "Rate limit exceeded",          # no "image" in message
        "prompt too long",              # size-ish word but about prompt, not image
        "Model unavailable",
        "Connection timeout",
        "Invalid JSON in response",
        "",
    ],
)
def test_is_image_size_error_false(message: str):
    assert is_image_size_error(ValueError(message)) is False


def test_is_image_size_error_unrelated_image_error():
    # Has "image" but no size hint — should NOT trigger retry.
    assert is_image_size_error(ValueError("failed to decode image")) is False


# ---------------------------------------------------------------------------
# downscale_png — resize behaviour
# ---------------------------------------------------------------------------

def test_downscale_png_already_small_short_circuits():
    png = _make_png(100, 100)
    result = downscale_png(png, max_long_edge=DEFAULT_MAX_LONG_EDGE)
    assert result.new_size is None
    assert result.png_bytes is png  # returns the exact input bytes, no re-encode
    assert result.original_size == (100, 100)


def test_downscale_png_shrinks_oversized_landscape():
    png = _make_png(4000, 3000)
    result = downscale_png(png, max_long_edge=2048)
    assert result.original_size == (4000, 3000)
    assert result.new_size is not None
    new_w, new_h = result.new_size
    assert max(new_w, new_h) == 2048
    # Aspect ratio preserved within 1 px rounding.
    assert abs((new_w / new_h) - (4000 / 3000)) < 0.01


def test_downscale_png_shrinks_oversized_portrait():
    png = _make_png(2000, 5000)
    result = downscale_png(png, max_long_edge=2048)
    assert result.new_size is not None
    new_w, new_h = result.new_size
    assert max(new_w, new_h) == 2048
    assert new_h > new_w  # still portrait


def test_downscale_png_returns_valid_png():
    """The downscaled bytes must be a decodable PNG."""
    png = _make_png(3000, 2000)
    result = downscale_png(png, max_long_edge=1024)
    assert result.new_size is not None
    # Round-trip: decode the output and check dimensions match.
    out = Image.open(io.BytesIO(result.png_bytes))
    assert out.format == "PNG"
    assert out.size == result.new_size


def test_downscale_png_at_boundary_not_resized():
    # Image exactly at max_long_edge should NOT be resized.
    png = _make_png(2048, 1024)
    result = downscale_png(png, max_long_edge=2048)
    assert result.new_size is None


def test_downscale_png_custom_max_edge():
    png = _make_png(4000, 4000)
    result = downscale_png(png, max_long_edge=1000)
    assert result.new_size == (1000, 1000)
