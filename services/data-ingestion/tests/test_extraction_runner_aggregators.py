"""Tests for the multi-chart aggregator helpers in ExtractionRunner (#36).

The per-chart aggregator functions are pure — given two parsed provider
responses for ONE chart, they return the consensus entries. The runner
glues these together across multiple charts.
"""

from __future__ import annotations

from decimal import Decimal

from shared.schemas.enums import FrequencyType, RunwaySurface

from app.services.extraction_runner import (
    _agreed_frequencies_on_chart,
    _agreed_geo_on_chart,
    _agreed_runways_on_chart,
)


def _ev(value, bbox=(0, 0, 1, 1)):
    """Build an ExtractedValue-shaped dict {value, bbox}."""
    return {"value": value, "bbox": list(bbox)}


# ---------------------------------------------------------------------------
# _agreed_geo_on_chart — returns only fields both providers matched
# ---------------------------------------------------------------------------

def test_geo_returns_agreed_fields_only():
    a = {
        "latitude_deg": _ev(48.3536),
        "longitude_deg": _ev(11.7858),
        "elevation_ft": _ev("1487 FT"),
        "city": _ev("Munich"),
        "operator": None,
    }
    b = {
        "latitude_deg": _ev(48.3538),   # within 0.001 float-tol
        "longitude_deg": _ev(11.7855),
        "elevation_ft": _ev(1487),
        "city": _ev("Munich"),
        "operator": _ev("Flughafen München"),  # only one side — excluded
    }
    out = _agreed_geo_on_chart(a, b)
    assert out["elevation_ft"] == 1487
    assert out["city"] == "Munich"
    assert "operator" not in out
    assert abs(out["latitude_deg"] - 48.3536) < 0.001


def test_geo_empty_when_nothing_agrees():
    a = {"city": _ev("Munich")}
    b = {"city": _ev("Berlin")}
    assert _agreed_geo_on_chart(a, b) == {}


def test_geo_handles_all_null_input():
    assert _agreed_geo_on_chart({}, {}) == {}


# ---------------------------------------------------------------------------
# _agreed_runways_on_chart
# ---------------------------------------------------------------------------

def test_runways_both_providers_report_same_rwy():
    a = {"runways": [{
        "designator_le": _ev("08L"),
        "designator_he": _ev("26R"),
        "length_m": _ev(4000),
        "width_m": _ev(60),
        "surface": _ev("asphalt"),
    }]}
    b = {"runways": [{
        "designator_le": _ev("08L"),
        "designator_he": _ev("26R"),
        "length_m": _ev("4000 m"),
        "width_m": _ev("60 m"),
        "surface": _ev("ASPHALT"),
    }]}
    out = _agreed_runways_on_chart(a, b)
    assert len(out) == 1
    assert out[0]["designator_le"] == "08L"
    assert out[0]["designator_he"] == "26R"
    assert out[0]["length_m"] == 4000
    assert out[0]["surface"] is RunwaySurface.ASPHALT


def test_runways_disagreeing_designators_dropped():
    a = {"runways": [{
        "designator_le": _ev("08L"),
        "designator_he": _ev("26R"),
    }]}
    b = {"runways": [{
        "designator_le": _ev("08L"),
        "designator_he": _ev("26L"),  # disagrees
    }]}
    assert _agreed_runways_on_chart(a, b) == []


def test_runways_only_in_one_provider_dropped():
    a = {"runways": [
        {"designator_le": _ev("08L"), "designator_he": _ev("26R")},
        {"designator_le": _ev("18"), "designator_he": _ev("36")},  # only in A
    ]}
    b = {"runways": [{
        "designator_le": _ev("08L"),
        "designator_he": _ev("26R"),
    }]}
    out = _agreed_runways_on_chart(a, b)
    assert len(out) == 1
    assert out[0]["designator_le"] == "08L"


def test_runways_missing_dims_still_included():
    """If providers agree on the runway identity, we accept it even if length
    / width / surface are null — the runway row itself is the 2-of-2 fact."""
    a = {"runways": [{
        "designator_le": _ev("07"),
        "designator_he": _ev("25"),
        "length_m": None,
        "width_m": None,
        "surface": None,
    }]}
    b = {"runways": [{
        "designator_le": _ev("07"),
        "designator_he": _ev("25"),
        "length_m": None,
        "width_m": None,
        "surface": None,
    }]}
    out = _agreed_runways_on_chart(a, b)
    assert len(out) == 1
    assert out[0]["length_m"] is None
    assert out[0]["surface"] is RunwaySurface.OTHER  # default


def test_runways_empty_lists_return_empty():
    assert _agreed_runways_on_chart({"runways": []}, {"runways": []}) == []
    assert _agreed_runways_on_chart({}, {}) == []


# HE-autofill (observed on EDDF chart 2: OpenAI drops designator_he for runway 18).
# Runway designators are always 180° apart so LE alone determines HE
# mathematically. We tolerate ONE provider dropping HE, not both
# disagreeing.

def test_runways_autofill_he_when_one_provider_drops_it():
    a = {"runways": [{
        "designator_le": _ev("18"),
        "designator_he": _ev("36"),
    }]}
    b = {"runways": [{
        "designator_le": _ev("18"),
        "designator_he": None,   # OpenAI dropped it
    }]}
    out = _agreed_runways_on_chart(a, b)
    assert len(out) == 1
    assert out[0]["designator_le"] == "18"
    assert out[0]["designator_he"] == "36"


def test_runways_autofill_he_when_both_providers_drop_it():
    a = {"runways": [{
        "designator_le": _ev("07L"),
        "designator_he": None,
    }]}
    b = {"runways": [{
        "designator_le": _ev("07L"),
        "designator_he": None,
    }]}
    out = _agreed_runways_on_chart(a, b)
    assert len(out) == 1
    assert out[0]["designator_le"] == "07L"
    assert out[0]["designator_he"] == "25R"  # 07L + 180° = 25R


def test_runways_reject_when_lone_he_disagrees_with_math():
    """One provider gave HE=29 for LE=07 — that's wrong and we won't pretend to agree."""
    a = {"runways": [{
        "designator_le": _ev("07"),
        "designator_he": _ev("29"),  # nonsense
    }]}
    b = {"runways": [{
        "designator_le": _ev("07"),
        "designator_he": None,
    }]}
    assert _agreed_runways_on_chart(a, b) == []


def test_runways_reject_when_both_provided_but_disagree():
    """Disagreement between providers on HE is never tie-broken by math."""
    a = {"runways": [{
        "designator_le": _ev("08L"),
        "designator_he": _ev("26R"),
    }]}
    b = {"runways": [{
        "designator_le": _ev("08L"),
        "designator_he": _ev("26L"),   # wrong
    }]}
    assert _agreed_runways_on_chart(a, b) == []


def test_runways_autofill_preserves_suffix_opposite():
    """07C ↔ 25C, 08L ↔ 26R, 08R ↔ 26L."""
    for le, expected_he in [("07C", "25C"), ("08L", "26R"), ("08R", "26L")]:
        a = {"runways": [{"designator_le": _ev(le), "designator_he": None}]}
        b = {"runways": [{"designator_le": _ev(le), "designator_he": None}]}
        out = _agreed_runways_on_chart(a, b)
        assert len(out) == 1, f"LE={le}"
        assert out[0]["designator_he"] == expected_he, f"LE={le} expected {expected_he}"


# Parallel same-designator runways (observed on EDFE Egelsbach: paved 08/26 plus
# a grass 08/26 strip with no L/R suffix).

def test_runways_parallel_same_le_kept_distinct_by_surface():
    """08 asphalt + 08 grass both reported → two agreed entries."""
    a = {"runways": [
        {"designator_le": _ev("08"), "designator_he": _ev("26"),
         "length_m": _ev("1400 M"), "width_m": _ev("25 M"), "surface": _ev("asphalt")},
        {"designator_le": _ev("08"), "designator_he": _ev("26"),
         "length_m": _ev("670 M"), "width_m": _ev("30 M"), "surface": _ev("grass")},
    ]}
    b = {"runways": [
        {"designator_le": _ev("08"), "designator_he": _ev("26"),
         "length_m": _ev(1400), "width_m": _ev(25), "surface": _ev("asphalt")},
        {"designator_le": _ev("08"), "designator_he": _ev("26"),
         "length_m": _ev(670), "width_m": _ev(30), "surface": _ev("grass")},
    ]}
    out = _agreed_runways_on_chart(a, b)
    assert len(out) == 2
    surfaces = [r["surface"] for r in out]
    assert RunwaySurface.ASPHALT in surfaces
    assert RunwaySurface.GRASS in surfaces


def test_runways_parallel_no_surface_split_by_length_bucket():
    """No surface but different length → length bucket disambiguates."""
    a = {"runways": [
        {"designator_le": _ev("08"), "designator_he": _ev("26"),
         "length_m": _ev(1400)},
        {"designator_le": _ev("08"), "designator_he": _ev("26"),
         "length_m": _ev(670)},
    ]}
    b = {"runways": [
        {"designator_le": _ev("08"), "designator_he": _ev("26"),
         "length_m": _ev(1400)},
        {"designator_le": _ev("08"), "designator_he": _ev("26"),
         "length_m": _ev(670)},
    ]}
    out = _agreed_runways_on_chart(a, b)
    assert len(out) == 2


# Disambiguation — multiple same-LE rows get suffixed for DB write.
from app.services.extraction_runner import _disambiguate_designators


def test_disambiguate_paved_keeps_raw_designator():
    rows = [
        {"designator_le": "08", "designator_he": "26",
         "length_m": 1400, "width_m": 25, "surface": RunwaySurface.ASPHALT},
        {"designator_le": "08", "designator_he": "26",
         "length_m": 670, "width_m": 30, "surface": RunwaySurface.GRASS},
    ]
    out = _disambiguate_designators(rows)
    assert len(out) == 2
    # Sorted primary-first — paved keeps raw designator, grass gets G suffix.
    primary = next(r for r in out if r["surface"] is RunwaySurface.ASPHALT)
    grass = next(r for r in out if r["surface"] is RunwaySurface.GRASS)
    assert primary["designator_le"] == "08"
    assert primary["designator_he"] == "26"
    assert grass["designator_le"] == "08G"
    assert grass["designator_he"] == "26G"


def test_disambiguate_single_runway_unchanged():
    rows = [{"designator_le": "08", "designator_he": "26",
             "length_m": 1400, "width_m": 25, "surface": RunwaySurface.ASPHALT}]
    out = _disambiguate_designators(rows)
    assert out[0]["designator_le"] == "08"


def test_disambiguate_distinct_le_untouched():
    rows = [
        {"designator_le": "08L", "designator_he": "26R",
         "length_m": 4000, "width_m": 60, "surface": RunwaySurface.ASPHALT},
        {"designator_le": "08R", "designator_he": "26L",
         "length_m": 4000, "width_m": 60, "surface": RunwaySurface.ASPHALT},
    ]
    out = _disambiguate_designators(rows)
    # Distinct LE keys — no suffixing needed.
    assert {r["designator_le"] for r in out} == {"08L", "08R"}


def test_disambiguate_concrete_beats_asphalt():
    rows = [
        {"designator_le": "07", "designator_he": "25",
         "length_m": 3000, "width_m": 45, "surface": RunwaySurface.ASPHALT},
        {"designator_le": "07", "designator_he": "25",
         "length_m": 4000, "width_m": 60, "surface": RunwaySurface.CONCRETE},
    ]
    out = _disambiguate_designators(rows)
    # Concrete comes first in _SURFACE_PRIMARY_ORDER; asphalt gets suffix X.
    primary = out[0]
    assert primary["surface"] is RunwaySurface.CONCRETE
    assert primary["designator_le"] == "07"
    assert out[1]["designator_le"] == "07X"


# ---------------------------------------------------------------------------
# _agreed_frequencies_on_chart
# ---------------------------------------------------------------------------

def test_frequencies_matched_by_type_and_value():
    a = {"frequencies": [
        {"type": _ev("twr"), "frequency_mhz": _ev("118.700"),
         "callsign": _ev("Munich Tower"), "callsign_de": _ev("München Turm"),
         "operational_hours": _ev("H24")},
    ]}
    b = {"frequencies": [
        {"type": _ev("twr"), "frequency_mhz": _ev("118.700"),
         "callsign": _ev("Munich Tower"), "callsign_de": None,
         "operational_hours": _ev("H24")},
    ]}
    out = _agreed_frequencies_on_chart(a, b)
    assert len(out) == 1
    assert out[0]["type"] is FrequencyType.TWR
    assert out[0]["frequency_mhz"] == Decimal("118.700")
    assert out[0]["callsign"] == "Munich Tower"
    assert out[0]["callsign_de"] is None  # only in A
    assert out[0]["operational_hours"] == "H24"


def test_frequencies_disagreeing_freq_dropped():
    a = {"frequencies": [
        {"type": _ev("twr"), "frequency_mhz": _ev("118.700")},
    ]}
    b = {"frequencies": [
        {"type": _ev("twr"), "frequency_mhz": _ev("118.705")},  # differs
    ]}
    assert _agreed_frequencies_on_chart(a, b) == []


def test_frequencies_unknown_type_dropped():
    a = {"frequencies": [
        {"type": _ev("xyz"), "frequency_mhz": _ev("118.700")},
    ]}
    b = {"frequencies": [
        {"type": _ev("xyz"), "frequency_mhz": _ev("118.700")},
    ]}
    assert _agreed_frequencies_on_chart(a, b) == []


def test_frequencies_case_insensitive_type_match():
    a = {"frequencies": [
        {"type": _ev("TWR"), "frequency_mhz": _ev("118.700")},
    ]}
    b = {"frequencies": [
        {"type": _ev("twr"), "frequency_mhz": _ev("118.700")},
    ]}
    out = _agreed_frequencies_on_chart(a, b)
    assert len(out) == 1
    assert out[0]["type"] is FrequencyType.TWR


def test_frequencies_multiple_entries_preserved_by_key():
    a = {"frequencies": [
        {"type": _ev("twr"), "frequency_mhz": _ev("118.700")},
        {"type": _ev("atis"), "frequency_mhz": _ev("123.125")},
        {"type": _ev("gnd"), "frequency_mhz": _ev("121.975")},
    ]}
    b = {"frequencies": [
        {"type": _ev("twr"), "frequency_mhz": _ev("118.700")},
        {"type": _ev("atis"), "frequency_mhz": _ev("123.125")},
        {"type": _ev("gnd"), "frequency_mhz": _ev("121.975")},
    ]}
    out = _agreed_frequencies_on_chart(a, b)
    assert len(out) == 3
    types = {e["type"] for e in out}
    assert types == {FrequencyType.TWR, FrequencyType.ATIS, FrequencyType.GND}
