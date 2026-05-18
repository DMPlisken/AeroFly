"""Unit tests for the chart-name classifier — pure functions, no I/O."""

from __future__ import annotations

import pytest

from app.scraper.classifier import (
    classify_chart_type,
    extract_chart_suffix,
    extract_icao,
    normalize_filename,
)


@pytest.mark.parametrize(
    "name, expected",
    [
        ("AD 2-71", "supplement"),
        ("AD 2-3", "supplement"),
        ("EDDM Munich Terminal Chart 1", "terminal"),
        ("EDDM Muenchen 4", "aerodrome"),
        ("EDDF Frankfurt Main 1", "aerodrome"),
        ("Some random doc", "other"),
    ],
)
def test_classify_chart_type(name, expected):
    assert classify_chart_type(name) == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("EDDM Muenchen 4", "4"),
        ("EDDH Hamburg 2A", "2A"),
        ("EDDF Frankfurt Main 1", "1"),
        ("EDDM Muenchen Terminal Chart 1", "1"),
        ("AD 2-71", None),
        ("EDDM", None),  # ICAO-only, no suffix after it
    ],
)
def test_extract_chart_suffix(name, expected):
    assert extract_chart_suffix(name) == expected


def test_normalize_filename():
    assert normalize_filename("EDKA Aachen-Merzbrueck 1") == "EDKA_Aachen-Merzbrueck_1"
    assert normalize_filename("AD 2-3") == "AD_2-3"
    assert normalize_filename("foo / bar") == "foo___bar"


def test_extract_icao():
    assert extract_icao("EDDF Frankfurt am Main") == "EDDF"
    assert extract_icao("Some text EDQM here") == "EDQM"
    assert extract_icao("nothing here") is None
