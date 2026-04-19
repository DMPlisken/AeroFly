"""Unit tests for unit_normalizer.py — pure functions, no external deps."""

from decimal import Decimal

import pytest

from app.parser.unit_normalizer import (
    UnitError,
    normalize,
    normalize_decimal_degree,
    normalize_elevation_to_ft,
    normalize_frequency_mhz,
    normalize_length_to_m,
    normalize_text,
)


class TestLengthNormalization:
    @pytest.mark.parametrize(
        "input_value,expected",
        [
            (4000, 4000),
            ("4000", 4000),
            ("4000 m", 4000),
            ("4000M", 4000),
            ("4 km", 4000),
            ("4 000 m", 4000),    # DFS-style space as thousands separator
        ],
    )
    def test_metres_passthrough(self, input_value, expected):
        assert normalize_length_to_m(input_value) == expected

    @pytest.mark.parametrize(
        "input_value,expected_m",
        [
            ("13123 ft", 4000),
            ("13123'", 4000),
            ("9843 ft", 3000),
            ("13 123 ft", 4000),   # space-thousands (DFS convention)
        ],
    )
    def test_feet_converted(self, input_value, expected_m):
        # Allow 1 m tolerance on rounding.
        assert abs(normalize_length_to_m(input_value) - expected_m) <= 1

    def test_ambiguous_dot_treated_as_decimal(self):
        """'4.000 m' is ambiguous (DE thousands vs EN decimal). DFS uses space
        for thousands, never dot; we therefore treat '.' as a decimal point.
        Callers extracting from non-DFS sources must pre-strip thousands seps."""
        assert normalize_length_to_m("4.000 m") == 4  # interpreted as 4.000 metres

    def test_unknown_unit_raises(self):
        with pytest.raises(UnitError):
            normalize_length_to_m("4000 leagues")


class TestElevationNormalization:
    def test_ft_passthrough(self):
        assert normalize_elevation_to_ft("1487 ft") == 1487

    def test_m_converted(self):
        # 453 m ≈ 1486 ft — depending on rounding 1485 or 1486.
        result = normalize_elevation_to_ft("453 m")
        assert 1484 <= result <= 1487


class TestFrequencyNormalization:
    @pytest.mark.parametrize(
        "input_value,expected",
        [
            ("118.700", Decimal("118.700")),
            ("118,700", Decimal("118.700")),
            ("118.7", Decimal("118.700")),
            (118.7, Decimal("118.700")),
            ("123.125", Decimal("123.125")),
        ],
    )
    def test_consistent_output(self, input_value, expected):
        assert normalize_frequency_mhz(input_value) == expected

    def test_khz_heuristic(self):
        # A bare integer like 118700 is ambiguous; we treat > 10 000 as kHz.
        assert normalize_frequency_mhz(118700) == Decimal("118.700")


class TestCoordinates:
    def test_decimal_passthrough(self):
        assert normalize_decimal_degree(48.3538) == pytest.approx(48.3538)

    def test_dms_north(self):
        # N 48° 21' 13"
        result = normalize_decimal_degree("N48°21'13\"")
        assert result == pytest.approx(48.3536, abs=0.001)

    def test_dms_west_negative(self):
        result = normalize_decimal_degree("W122°30'00\"")
        assert result == pytest.approx(-122.5, abs=0.001)

    def test_hemisphere_suffix(self):
        result = normalize_decimal_degree("48°21'13\"N")
        assert result == pytest.approx(48.3536, abs=0.001)

    def test_unparseable(self):
        with pytest.raises(UnitError):
            normalize_decimal_degree("not a coord")


class TestText:
    def test_trims_and_collapses(self):
        assert normalize_text("  Munich\n  Airport  ") == "Munich Airport"

    def test_nfc_normalization(self):
        # "Mu\u0308nchen" (NFD) should become "München" (NFC).
        assert normalize_text("Mu\u0308nchen") == "München"


class TestDispatch:
    def test_normalize_by_field(self):
        assert normalize("length_m", "13123 ft") == 4000
        assert normalize("elevation_ft", "453 m") in (1485, 1486, 1487)
        assert normalize("frequency_mhz", "118,700") == Decimal("118.700")
        assert normalize("city", "  München  ") == "München"

    def test_normalize_null_passes(self):
        assert normalize("anything", None) is None
