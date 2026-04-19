"""Unit tests for consensus.py — pure decision function.

These tests are the safety core. Every permutation that could produce a
false-positive acceptance needs a test here.
"""

from decimal import Decimal

import pytest

from app.parser.consensus import (
    ConsensusDecision,
    RiskClass,
    SourceKind,
    SourceVote,
    reach_consensus,
)
from app.parser.domain_validator import (
    validate_elevation_ft,
    validate_frequency_mhz,
    validate_runway_length_m,
)


def _vote(kind: SourceKind, value):
    return SourceVote(kind=kind, value=value)


# ---------------------------------------------------------------- HAPPY PATHS


class TestAcceptance:
    def test_3_of_3_accepts_critical(self):
        decision = reach_consensus(
            field="frequency_mhz",
            risk=RiskClass.CRITICAL,
            votes=[
                _vote(SourceKind.LLM_A, "118.700"),
                _vote(SourceKind.LLM_B, "118.700"),
                _vote(SourceKind.OCR, "118.700"),
            ],
            domain_validator=validate_frequency_mhz,
        )
        assert decision.persisted_value == Decimal("118.700")
        assert decision.result == "accepted_3_of_3"
        assert len(decision.contributing_sources) == 3

    def test_2_of_2_accepts_high(self):
        decision = reach_consensus(
            field="elevation_ft",
            risk=RiskClass.HIGH,
            votes=[
                _vote(SourceKind.LLM_A, "1487 ft"),
                _vote(SourceKind.LLM_B, "1487"),
            ],
            domain_validator=validate_elevation_ft,
        )
        assert decision.persisted_value == 1487
        assert decision.result == "accepted_2_of_3"

    def test_html_plus_one_wins(self):
        decision = reach_consensus(
            field="elevation_ft",
            risk=RiskClass.HIGH,
            votes=[
                _vote(SourceKind.HTML, "1487"),
                _vote(SourceKind.LLM_A, "1487"),
            ],
            domain_validator=validate_elevation_ft,
        )
        assert decision.result == "accepted_html_anchored"
        assert decision.persisted_value == 1487

    def test_normalization_collapses_units(self):
        """4000 m and 13123 ft must be considered the same value."""
        decision = reach_consensus(
            field="length_m",
            risk=RiskClass.CRITICAL,
            votes=[
                _vote(SourceKind.LLM_A, "4000 m"),
                _vote(SourceKind.LLM_B, "13123 ft"),
                _vote(SourceKind.OCR, "4000"),
            ],
            domain_validator=validate_runway_length_m,
        )
        assert decision.persisted_value == 4000


# --------------------------------------------------------------- FAIL-CLOSED


class TestRejection:
    def test_critical_with_only_2_of_3_rejected(self):
        decision = reach_consensus(
            field="frequency_mhz",
            risk=RiskClass.CRITICAL,
            votes=[
                _vote(SourceKind.LLM_A, "118.700"),
                _vote(SourceKind.LLM_B, "118.700"),
                _vote(SourceKind.OCR, "119.700"),  # disagrees
            ],
            domain_validator=validate_frequency_mhz,
        )
        assert decision.persisted_value is None
        assert decision.result == "rejected_disagreement"
        assert decision.needs_human_review is True

    def test_all_disagree_rejected(self):
        decision = reach_consensus(
            field="elevation_ft",
            risk=RiskClass.HIGH,
            votes=[
                _vote(SourceKind.LLM_A, "1487"),
                _vote(SourceKind.LLM_B, "1500"),
                _vote(SourceKind.OCR, "1480"),
            ],
            domain_validator=validate_elevation_ft,
        )
        assert decision.persisted_value is None
        assert decision.result in (
            "rejected_disagreement",
            "rejected_insufficient_sources",
        )

    def test_empty_votes_rejected(self):
        decision = reach_consensus(
            field="frequency_mhz",
            risk=RiskClass.CRITICAL,
            votes=[],
            domain_validator=validate_frequency_mhz,
        )
        assert decision.persisted_value is None
        assert decision.result == "rejected_insufficient_sources"
        assert decision.needs_human_review is True

    def test_only_nulls_rejected(self):
        decision = reach_consensus(
            field="frequency_mhz",
            risk=RiskClass.CRITICAL,
            votes=[
                _vote(SourceKind.LLM_A, None),
                _vote(SourceKind.LLM_B, None),
                _vote(SourceKind.OCR, None),
            ],
            domain_validator=validate_frequency_mhz,
        )
        assert decision.persisted_value is None

    def test_domain_violation_rejects_despite_consensus(self):
        """Even 3/3 agreement cannot override physical impossibility."""
        decision = reach_consensus(
            field="frequency_mhz",
            risk=RiskClass.CRITICAL,
            votes=[
                _vote(SourceKind.LLM_A, "999.999"),
                _vote(SourceKind.LLM_B, "999.999"),
                _vote(SourceKind.OCR, "999.999"),
            ],
            domain_validator=validate_frequency_mhz,
        )
        assert decision.persisted_value is None
        assert decision.result == "rejected_domain"
        assert decision.needs_human_review is True

    def test_html_vs_others_disagreement_rejects(self):
        """HTML says A, everyone else says B → reject, needs review."""
        decision = reach_consensus(
            field="elevation_ft",
            risk=RiskClass.HIGH,
            votes=[
                _vote(SourceKind.HTML, "1500"),
                _vote(SourceKind.LLM_A, "1487"),
                _vote(SourceKind.LLM_B, "1487"),
            ],
            domain_validator=validate_elevation_ft,
        )
        assert decision.persisted_value is None
        assert decision.result == "rejected_disagreement"

    def test_unit_parse_failure_counts_as_reject(self):
        decision = reach_consensus(
            field="length_m",
            risk=RiskClass.CRITICAL,
            votes=[
                _vote(SourceKind.LLM_A, "4000 m"),
                _vote(SourceKind.LLM_B, "4000"),
                _vote(SourceKind.OCR, "garbage-text"),
            ],
            domain_validator=validate_runway_length_m,
        )
        # Only 2 out of 3 parseable → CRITICAL needs 3 → reject.
        assert decision.persisted_value is None

    def test_low_risk_accepts_single_source(self):
        decision = reach_consensus(
            field="remark",
            risk=RiskClass.LOW,
            votes=[_vote(SourceKind.LLM_A, "No night operations")],
        )
        assert decision.persisted_value == "No night operations"
        assert decision.result == "accepted_single_source"


# ------------------------------------------------- REGRESSION: THE CLASSIC TRAPS


class TestClassicTraps:
    def test_mars_climate_orbiter_unit_mismatch(self):
        """One source says 4000 (implied m), another says 4000 ft. They should NOT agree."""
        decision = reach_consensus(
            field="length_m",
            risk=RiskClass.CRITICAL,
            votes=[
                _vote(SourceKind.LLM_A, "4000 m"),
                _vote(SourceKind.LLM_B, "4000 ft"),   # 1219 m normalized
                _vote(SourceKind.OCR, "4000 m"),
            ],
            domain_validator=validate_runway_length_m,
        )
        # LLM_A and OCR agree at 4000 m; LLM_B normalizes to 1219 m.
        # Only 2 of 3 → insufficient for CRITICAL.
        assert decision.persisted_value is None

    def test_frequency_off_grid_rejected(self):
        decision = reach_consensus(
            field="frequency_mhz",
            risk=RiskClass.CRITICAL,
            votes=[
                _vote(SourceKind.LLM_A, "118.123"),  # off the 25 / 8.33 kHz grid
                _vote(SourceKind.LLM_B, "118.123"),
                _vote(SourceKind.OCR, "118.123"),
            ],
            domain_validator=validate_frequency_mhz,
        )
        assert decision.persisted_value is None
        assert decision.result == "rejected_domain"
