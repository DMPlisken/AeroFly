"""Unit tests for the DFS chart-name classifier.

Run from the repo root:
    pytest scripts/test_chart_classifier.py -v
"""

from __future__ import annotations

import pytest

from scrape_dfs_aip import classify_chart_type, extract_chart_suffix


@pytest.mark.parametrize(
    "dfs_name, expected",
    [
        # Supplements — shared AD references, no airport ICAO in the name.
        ("AD 2-71", "supplement"),
        ("AD 2-3", "supplement"),
        ("AD 2-35", "supplement"),
        ("AD 2-42", "supplement"),
        ("  AD 2-71  ", "supplement"),

        # Terminal charts.
        ("EDDM Muenchen Terminal Chart 1", "terminal"),
        ("EDDF Frankfurt Main Terminal Chart", "terminal"),
        ("EDDH Hamburg Terminal Chart", "terminal"),

        # Per-airport charts (aerodrome bucket — subtype left to selector).
        ("EDDM Muenchen 1", "aerodrome"),
        ("EDDM Muenchen 4", "aerodrome"),
        ("EDDH Hamburg 2A", "aerodrome"),
        ("EDDH Hamburg 2B", "aerodrome"),
        ("EDKA Aachen-Merzbrueck 1", "aerodrome"),
        ("EDDF Frankfurt Main 5", "aerodrome"),

        # Fallback — text that does not start with an airport ICAO and is not an AD ref.
        ("Random unknown document", "other"),
        ("Miscellaneous page", "other"),
    ],
)
def test_classify_chart_type(dfs_name: str, expected: str):
    assert classify_chart_type(dfs_name) == expected


def test_classify_empty_string():
    assert classify_chart_type("") == "other"


@pytest.mark.parametrize(
    "dfs_name, expected",
    [
        ("EDDM Muenchen 1", "1"),
        ("EDDM Muenchen 4", "4"),
        ("EDDH Hamburg 2A", "2A"),
        ("EDDH Hamburg 2B", "2B"),
        ("EDDF Frankfurt Main 5", "5"),
        ("EDDM Muenchen Terminal Chart 1", "1"),
        ("EDKA Aachen-Merzbrueck 1", "1"),

        # No airport ICAO prefix -> no suffix extracted (supplement case).
        ("AD 2-71", None),
        ("AD 2-3", None),

        # Not starting with ICAO -> no suffix.
        ("Some other page", None),
    ],
)
def test_extract_chart_suffix(dfs_name: str, expected):
    assert extract_chart_suffix(dfs_name) == expected
