"""Unit tests for grounding.py.

Tests the pure logic paths (substring matching, field-skip policy, no-bbox
handling). Actual tesseract calls are exercised in integration tests that
need the binary.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from app.parser.grounding import (
    GroundingResult,
    SKIP_GROUNDING_FIELDS,
    _strip_for_grounding,
    ground,
    ground_any,
    value_present_in_text,
)


class TestStripForGrounding:
    def test_alnum_only_lowercase(self):
        assert _strip_for_grounding("FREQ 118.700 MHz") == "freq118700mhz"

    def test_nfc_umlauts(self):
        # Decomposed 'u' + combining diaeresis → 'ü'
        decomposed = "Mu\u0308nchen"
        assert _strip_for_grounding(decomposed) == "münchen"


class TestValuePresent:
    def test_frequency_found(self):
        assert value_present_in_text("118.700", "FREQ 118.700 MHz Tower") is True

    def test_integer_found(self):
        assert value_present_in_text(1487, "ELEV 1487 FT") is True

    def test_missing(self):
        assert value_present_in_text("118.700", "ELEV 1487 FT") is False

    def test_none_value(self):
        assert value_present_in_text(None, "any text") is False

    def test_digits_across_punctuation(self):
        # Tesseract output "FREQ 118,700" must still ground "118.700".
        assert value_present_in_text("118.700", "FREQ 118,700 MHz") is True


class TestFieldPolicy:
    @pytest.mark.parametrize("field", sorted(SKIP_GROUNDING_FIELDS))
    def test_skip_grounding_fields_always_grounded(self, field, tmp_path: Path):
        result = ground(
            field=field,
            claimed_value=48.3538,
            image_path=tmp_path / "fake.png",
            bbox=(0, 0, 10, 10),
        )
        assert result.grounded is True
        assert result.reason == "grounding_skipped_by_field_policy"


class TestNoBboxOrValue:
    def test_no_bbox_rejected(self, tmp_path: Path):
        result = ground(
            field="length_m",
            claimed_value=4000,
            image_path=tmp_path / "fake.png",
            bbox=None,
        )
        assert result.grounded is False
        assert result.reason == "no_bbox_from_llm"

    def test_no_value_rejected(self, tmp_path: Path):
        result = ground(
            field="length_m",
            claimed_value=None,
            image_path=tmp_path / "fake.png",
            bbox=(1, 1, 2, 2),
        )
        assert result.grounded is False
        assert result.reason == "no_claimed_value"


class TestGroundingWithMockOCR:
    """Tests the ground() plumbing by patching the low-level _ocr_png_bytes."""

    def test_ocr_confirms(self, tmp_path: Path):
        # Create a tiny PNG so PIL can open it.
        from PIL import Image

        img_path = tmp_path / "sample.png"
        Image.new("RGB", (100, 100), color="white").save(img_path)

        with patch(
            "app.parser.grounding._ocr_png_bytes",
            return_value="FREQ 118.700 MHz TWR",
        ):
            result = ground(
                field="frequency_mhz",
                claimed_value="118.700",
                image_path=img_path,
                bbox=(10, 10, 50, 50),
            )
        assert result.grounded is True
        assert result.reason == "value_substring_found_in_ocr"

    def test_ocr_does_not_confirm(self, tmp_path: Path):
        from PIL import Image
        img_path = tmp_path / "sample.png"
        Image.new("RGB", (100, 100), color="white").save(img_path)

        with patch(
            "app.parser.grounding._ocr_png_bytes",
            return_value="qwerty !!!",
        ):
            result = ground(
                field="frequency_mhz",
                claimed_value="118.700",
                image_path=img_path,
                bbox=(10, 10, 50, 50),
            )
        assert result.grounded is False
        assert result.reason == "value_not_present_in_ocr"

    def test_ground_any_passes_if_either_bbox_matches(self, tmp_path: Path):
        from PIL import Image
        img_path = tmp_path / "sample.png"
        Image.new("RGB", (100, 100), color="white").save(img_path)

        # First bbox OCR fails, second succeeds — any() must accept.
        with patch(
            "app.parser.grounding._ocr_png_bytes",
            side_effect=["irrelevant text", "FREQ 118.700 MHz"],
        ):
            result = ground_any(
                field="frequency_mhz",
                claimed_value="118.700",
                image_path=img_path,
                bboxes=[(10, 10, 50, 50), (20, 20, 60, 60)],
            )
        assert result.grounded is True

    def test_ground_any_rejects_if_no_bbox_matches(self, tmp_path: Path):
        from PIL import Image
        img_path = tmp_path / "sample.png"
        Image.new("RGB", (100, 100), color="white").save(img_path)

        with patch(
            "app.parser.grounding._ocr_png_bytes",
            return_value="nothing relevant",
        ):
            result = ground_any(
                field="frequency_mhz",
                claimed_value="118.700",
                image_path=img_path,
                bboxes=[(10, 10, 50, 50), (20, 20, 60, 60)],
            )
        assert result.grounded is False
