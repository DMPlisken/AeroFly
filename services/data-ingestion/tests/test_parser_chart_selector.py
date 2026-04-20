"""Tests for the manifest-driven chart selector.

No Tesseract calls. Synthetic manifest.json + empty PNG files on disk
exercise the filter + ranking logic in isolation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.parser.chart_selector import pick_chart, rank_charts


def _make_manifest(tmp_path: Path, documents: list[dict]) -> Path:
    """Write a synthetic manifest and create each referenced print_file."""
    aerodrome_dir = tmp_path / "EDXX"
    aerodrome_dir.mkdir()
    for doc in documents:
        pf = doc.get("print_file")
        if pf:
            (aerodrome_dir / pf).write_bytes(b"\x89PNG\r\n")  # stub bytes
    manifest = {
        "icao": "EDXX",
        "name": "Testfield",
        "edition": "2026APR02",
        "scraped_at": "2026-04-20T00:00:00",
        "documents": documents,
    }
    (aerodrome_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return aerodrome_dir


# ---------------------------------------------------------------------------
# Empty / missing cases
# ---------------------------------------------------------------------------

def test_returns_empty_when_dir_missing(tmp_path):
    assert rank_charts(tmp_path / "nonexistent", field_group="geo") == []


def test_returns_empty_when_manifest_missing(tmp_path):
    (tmp_path / "EDXX").mkdir()
    assert rank_charts(tmp_path / "EDXX", field_group="geo") == []


def test_returns_empty_when_no_accepted_chart_types(tmp_path):
    aerodrome_dir = _make_manifest(tmp_path, [
        {"dfs_name": "AD 2-71", "chart_type": "supplement", "chart_suffix": None,
         "print_file": "AD_2-71.png"},
        {"dfs_name": "Junk", "chart_type": "other", "chart_suffix": None,
         "print_file": "Junk.png"},
    ])
    assert rank_charts(aerodrome_dir, field_group="geo") == []


# ---------------------------------------------------------------------------
# Filtering by chart_type
# ---------------------------------------------------------------------------

def test_geo_accepts_aerodrome_and_terminal(tmp_path):
    aerodrome_dir = _make_manifest(tmp_path, [
        {"dfs_name": "AD 2-71", "chart_type": "supplement", "chart_suffix": None,
         "print_file": "supp.png"},
        {"dfs_name": "EDXX Test Terminal Chart 1", "chart_type": "terminal",
         "chart_suffix": "1", "print_file": "term.png"},
        {"dfs_name": "EDXX Test 4", "chart_type": "aerodrome", "chart_suffix": "4",
         "print_file": "adc.png"},
    ])
    ranked = rank_charts(aerodrome_dir, field_group="geo")
    names = [c.path.name for c in ranked]
    assert "supp.png" not in names
    assert {"term.png", "adc.png"} == set(names)


def test_runways_only_accepts_aerodrome(tmp_path):
    aerodrome_dir = _make_manifest(tmp_path, [
        {"dfs_name": "EDXX Test Terminal Chart 1", "chart_type": "terminal",
         "chart_suffix": "1", "print_file": "term.png"},
        {"dfs_name": "EDXX Test 4", "chart_type": "aerodrome", "chart_suffix": "4",
         "print_file": "adc.png"},
    ])
    ranked = rank_charts(aerodrome_dir, field_group="runways")
    assert [c.path.name for c in ranked] == ["adc.png"]


# ---------------------------------------------------------------------------
# Ranking by chart_suffix priority
# ---------------------------------------------------------------------------

def test_geo_prefers_suffix_1_then_2_then_4(tmp_path):
    # geo priority: "1" -> "2" -> "4"
    aerodrome_dir = _make_manifest(tmp_path, [
        {"dfs_name": "EDXX Test 4", "chart_type": "aerodrome", "chart_suffix": "4",
         "print_file": "d4.png"},
        {"dfs_name": "EDXX Test 1", "chart_type": "aerodrome", "chart_suffix": "1",
         "print_file": "d1.png"},
        {"dfs_name": "EDXX Test 2", "chart_type": "aerodrome", "chart_suffix": "2",
         "print_file": "d2.png"},
    ])
    ranked = rank_charts(aerodrome_dir, field_group="geo")
    assert [c.path.name for c in ranked] == ["d1.png", "d2.png", "d4.png"]


def test_runways_prefers_suffix_4_then_1_then_2(tmp_path):
    # runways priority: "4" -> "1" -> "2"
    aerodrome_dir = _make_manifest(tmp_path, [
        {"dfs_name": "EDXX Test 1", "chart_type": "aerodrome", "chart_suffix": "1",
         "print_file": "d1.png"},
        {"dfs_name": "EDXX Test 2", "chart_type": "aerodrome", "chart_suffix": "2",
         "print_file": "d2.png"},
        {"dfs_name": "EDXX Test 4", "chart_type": "aerodrome", "chart_suffix": "4",
         "print_file": "d4.png"},
    ])
    ranked = rank_charts(aerodrome_dir, field_group="runways")
    assert [c.path.name for c in ranked] == ["d4.png", "d1.png", "d2.png"]


def test_unknown_suffix_sorts_after_known(tmp_path):
    aerodrome_dir = _make_manifest(tmp_path, [
        {"dfs_name": "EDXX Test 2A", "chart_type": "aerodrome", "chart_suffix": "2A",
         "print_file": "d2a.png"},
        {"dfs_name": "EDXX Test 1", "chart_type": "aerodrome", "chart_suffix": "1",
         "print_file": "d1.png"},
    ])
    ranked = rank_charts(aerodrome_dir, field_group="geo")
    # "1" is in priority tuple, "2A" is not → known wins.
    assert ranked[0].path.name == "d1.png"
    assert ranked[1].path.name == "d2a.png"


# ---------------------------------------------------------------------------
# Data hygiene
# ---------------------------------------------------------------------------

def test_missing_print_file_excluded(tmp_path):
    """A manifest entry without a print_file on disk must not be yielded."""
    aerodrome_dir = tmp_path / "EDXX"
    aerodrome_dir.mkdir()
    manifest = {
        "icao": "EDXX",
        "name": "Testfield",
        "edition": "2026APR02",
        "scraped_at": "2026-04-20T00:00:00",
        "documents": [
            {"dfs_name": "EDXX Test 1", "chart_type": "aerodrome",
             "chart_suffix": "1", "print_file": "d1.png"},  # not written to disk
        ],
    }
    (aerodrome_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert rank_charts(aerodrome_dir, field_group="geo") == []


def test_null_print_file_excluded(tmp_path):
    aerodrome_dir = _make_manifest(tmp_path, [
        {"dfs_name": "EDXX Test 1", "chart_type": "aerodrome", "chart_suffix": "1",
         "print_file": None},
    ])
    assert rank_charts(aerodrome_dir, field_group="geo") == []


# ---------------------------------------------------------------------------
# pick_chart convenience
# ---------------------------------------------------------------------------

def test_pick_chart_returns_first_ranked(tmp_path):
    aerodrome_dir = _make_manifest(tmp_path, [
        {"dfs_name": "EDXX Test 4", "chart_type": "aerodrome", "chart_suffix": "4",
         "print_file": "d4.png"},
        {"dfs_name": "EDXX Test 1", "chart_type": "aerodrome", "chart_suffix": "1",
         "print_file": "d1.png"},
    ])
    picked = pick_chart(aerodrome_dir, field_group="geo")
    assert picked is not None
    assert picked.path.name == "d1.png"
    assert picked.chart_type == "aerodrome"
    assert picked.chart_suffix == "1"


def test_pick_chart_none_when_no_candidates(tmp_path):
    aerodrome_dir = _make_manifest(tmp_path, [
        {"dfs_name": "AD 2-71", "chart_type": "supplement",
         "chart_suffix": None, "print_file": "supp.png"},
    ])
    assert pick_chart(aerodrome_dir, field_group="geo") is None


# ---------------------------------------------------------------------------
# FieldGroup coverage — every declared group has a mapping
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "field_group",
    ["geo", "runways", "frequencies", "obstacles", "reporting_points"],
)
def test_every_field_group_mapped(tmp_path, field_group):
    # Even if no candidates match, the call must not raise.
    aerodrome_dir = _make_manifest(tmp_path, [
        {"dfs_name": "EDXX Test 1", "chart_type": "aerodrome", "chart_suffix": "1",
         "print_file": "d1.png"},
    ])
    ranked = rank_charts(aerodrome_dir, field_group=field_group)
    assert len(ranked) == 1  # aerodrome type is accepted for all five groups
