"""Tests for the pure-function helpers in ExtractionRunner.

Runner orchestration is covered end-to-end by manual validation on
EDDM (see PR #35). These tests focus on the consensus / merge logic
that decides which values land in the DB.
"""

from __future__ import annotations

import pytest

from shared.schemas.enums import FrequencyType, RunwaySurface

from app.services.extraction_runner import (
    _agree,
    _agree_int_with_unit,
    _has_signal,
    _map_freq_type,
    _map_surface,
    _unwrap,
)


# ---------------------------------------------------------------------------
# _has_signal
# ---------------------------------------------------------------------------

def test_has_signal_true_on_single_value():
    parsed = {"latitude_deg": {"value": 48.3, "bbox": [0, 0, 1, 1]}}
    assert _has_signal(parsed) is True


def test_has_signal_false_on_all_nulls():
    parsed = {
        "latitude_deg": None,
        "longitude_deg": {"value": None, "bbox": None},
    }
    assert _has_signal(parsed) is False


def test_has_signal_true_on_nonempty_list():
    parsed = {"runways": [{"designator_le": {"value": "08L", "bbox": [0, 0, 1, 1]}}]}
    assert _has_signal(parsed) is True


def test_has_signal_false_on_empty_list():
    assert _has_signal({"runways": []}) is False


def test_has_signal_handles_none():
    assert _has_signal(None) is False


# ---------------------------------------------------------------------------
# _unwrap
# ---------------------------------------------------------------------------

def test_unwrap_returns_inner_value():
    assert _unwrap({"value": "Munich", "bbox": [0, 0, 1, 1]}) == "Munich"


def test_unwrap_passes_through_plain_string():
    assert _unwrap("Munich") == "Munich"


def test_unwrap_none():
    assert _unwrap(None) is None


# ---------------------------------------------------------------------------
# _agree — string equality + float tolerance
# ---------------------------------------------------------------------------

def test_agree_exact_string():
    assert _agree("Munich", "Munich") == "Munich"


def test_agree_trimmed_and_case_insensitive():
    assert _agree(" munich ", "MUNICH") == "munich"


def test_agree_disagreeing_strings():
    assert _agree("Munich", "Frankfurt") is None


def test_agree_float_within_tolerance():
    assert _agree(48.3536, 48.3539, float_tol=0.01) is not None


def test_agree_float_outside_tolerance():
    assert _agree(48.3, 48.4, float_tol=0.01) is None


def test_agree_unwraps_wrapper():
    a = {"value": "Munich", "bbox": [0, 0, 1, 1]}
    b = {"value": "Munich", "bbox": [0, 0, 1, 1]}
    assert _agree(a, b) == "Munich"


def test_agree_null_side_returns_none():
    assert _agree(None, "Munich") is None
    assert _agree({"value": None}, "Munich") is None


# ---------------------------------------------------------------------------
# _agree_int_with_unit — elevation/length parsing
# ---------------------------------------------------------------------------

def test_agree_int_with_unit_ft_string():
    assert _agree_int_with_unit("1487 FT", "1487 FT") == 1487


def test_agree_int_with_unit_slack_two_ft():
    # Rounding slack: 1487 vs 1488 should still agree.
    assert _agree_int_with_unit("1487 FT", "1488 FT") == 1487


def test_agree_int_with_unit_disagree():
    assert _agree_int_with_unit("1487 FT", "1500 FT") is None


def test_agree_int_with_unit_different_unit_token_same_number():
    # Prompt sometimes returns "453 M" and sometimes "453m" — still agrees.
    assert _agree_int_with_unit("453 M", "453 m") == 453


def test_agree_int_with_unit_integer_input():
    assert _agree_int_with_unit(4000, 4000) == 4000


# ---------------------------------------------------------------------------
# _map_surface — enum lookup
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("asphalt", RunwaySurface.ASPHALT),
        ("ASPHALT", RunwaySurface.ASPHALT),
        ("beton", RunwaySurface.CONCRETE),
        ("concrete", RunwaySurface.CONCRETE),
        ("asphalt/concrete", RunwaySurface.ASPHALT),
        ("gras", RunwaySurface.GRASS),
        ("schotter", RunwaySurface.GRAVEL),
        ("unknownmat", RunwaySurface.OTHER),
        (None, RunwaySurface.OTHER),
        ("", RunwaySurface.OTHER),
    ],
)
def test_map_surface(raw, expected):
    assert _map_surface(raw) is expected


# ---------------------------------------------------------------------------
# _map_freq_type — canonical enum from prompt output
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("twr", FrequencyType.TWR),
        ("TWR", FrequencyType.TWR),
        ("tower", FrequencyType.TWR),   # English alias
        ("gnd", FrequencyType.GND),
        ("ground", FrequencyType.GND),  # English alias
        ("atis", FrequencyType.ATIS),
        ("info", FrequencyType.INFO),
        ("information", FrequencyType.INFO),
        ("del", FrequencyType.DEL),
        ("delivery", FrequencyType.DEL),
        ("unknown_type", None),
    ],
)
def test_map_freq_type(raw, expected):
    assert _map_freq_type(raw) is expected
