"""Unit tests for domain_validator.py — no external deps."""

from decimal import Decimal

import pytest

from app.parser.domain_validator import (
    ValidationError,
    validate_airac_cycle,
    validate_elevation_ft,
    validate_frequency_mhz,
    validate_icao,
    validate_latitude,
    validate_longitude,
    validate_mag_variation,
    validate_runway_designator,
    validate_runway_heading_vs_designator,
    validate_runway_length_m,
    validate_runway_width_m,
)


class TestRunwayLength:
    def test_in_range(self):
        assert validate_runway_length_m(2500) == 2500

    @pytest.mark.parametrize("bad", [0, 100, 199, 6001, 40000])
    def test_out_of_range_rejected(self, bad):
        with pytest.raises(ValidationError):
            validate_runway_length_m(bad)


class TestRunwayWidth:
    def test_in_range(self):
        assert validate_runway_width_m(45) == 45

    def test_too_wide(self):
        with pytest.raises(ValidationError):
            validate_runway_width_m(200)

    def test_too_narrow(self):
        with pytest.raises(ValidationError):
            validate_runway_width_m(3)


class TestElevation:
    def test_eddm_plausible(self):
        assert validate_elevation_ft(1487) == 1487

    def test_negative_ok_for_netherlands_adjacent(self):
        assert validate_elevation_ft(-100) == -100

    @pytest.mark.parametrize("bad", [-500, 20000, 100000])
    def test_implausible_rejected(self, bad):
        with pytest.raises(ValidationError):
            validate_elevation_ft(bad)


class TestMagneticVariation:
    def test_central_europe(self):
        assert validate_mag_variation(Decimal("2.5")) == Decimal("2.5")

    def test_too_large(self):
        with pytest.raises(ValidationError):
            validate_mag_variation(Decimal("20.0"))


class TestFrequency:
    @pytest.mark.parametrize("good", ["118.700", "121.500", "123.125", "136.975"])
    def test_vhf_band_ok(self, good):
        assert validate_frequency_mhz(good) == Decimal(good)

    @pytest.mark.parametrize("bad", ["100.000", "140.000", "999.999", "50.000"])
    def test_outside_band(self, bad):
        with pytest.raises(ValidationError):
            validate_frequency_mhz(bad)

    def test_wrong_channel_grid(self):
        # 118.123 is neither on 25 kHz nor 8.33 kHz grid.
        with pytest.raises(ValidationError):
            validate_frequency_mhz("118.123")


class TestCoordinates:
    def test_eddm_latitude(self):
        assert validate_latitude(48.35) == 48.35

    def test_eddm_longitude(self):
        assert validate_longitude(11.78) == 11.78

    def test_latitude_outside_germany(self):
        with pytest.raises(ValidationError):
            validate_latitude(0)

    def test_longitude_outside_germany(self):
        with pytest.raises(ValidationError):
            validate_longitude(-5)


class TestRunwayDesignator:
    @pytest.mark.parametrize("good", ["08L", "26R", "18", "36", "07C"])
    def test_valid(self, good):
        assert validate_runway_designator(good) == good

    @pytest.mark.parametrize(
        "bad",
        ["0", "37", "ABC", "08Q", "888", ""],
    )
    def test_invalid(self, bad):
        with pytest.raises(ValidationError):
            validate_runway_designator(bad)


class TestRunwayHeading:
    def test_08l_with_heading_80(self):
        # 08 → 80° ± 10°.
        validate_runway_heading_vs_designator("08L", 80)
        validate_runway_heading_vs_designator("08L", 84)
        validate_runway_heading_vs_designator("08L", 76)

    def test_08_with_heading_100_rejected(self):
        with pytest.raises(ValidationError):
            validate_runway_heading_vs_designator("08L", 100)

    def test_36_with_heading_358_ok(self):
        # 36 → 360° / 0°; heading 358 is 2° away modulo 360.
        validate_runway_heading_vs_designator("36", 358)

    def test_runway_mislabelled_detected(self):
        # A runway labelled 08 but really heading 210 — classic wrong-label error.
        with pytest.raises(ValidationError):
            validate_runway_heading_vs_designator("08L", 210)


class TestIcao:
    def test_valid(self):
        assert validate_icao("eddm") == "EDDM"

    @pytest.mark.parametrize("bad", ["ED", "EDDMX", "12DM", ""])
    def test_invalid(self, bad):
        with pytest.raises(ValidationError):
            validate_icao(bad)


class TestAiracCycle:
    def test_valid(self):
        assert validate_airac_cycle("2026-04") == "2026-04"

    @pytest.mark.parametrize("bad", ["2026-13", "2026/04", "26-04", "1999-04"])
    def test_invalid(self, bad):
        with pytest.raises(ValidationError):
            validate_airac_cycle(bad)
