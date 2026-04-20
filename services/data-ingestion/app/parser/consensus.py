"""Consensus engine — decides whether extracted values may be persisted.

See section §04 of docs/reports/2026-04-19-chart-extraction-rocksolid-plan.html
for the full logic and the §05 risk-class table.

Pure function. Deterministic. No I/O. Safety-critical.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .domain_validator import ValidationError
from .unit_normalizer import UnitError, normalize


class RiskClass(str, Enum):
    CRITICAL = "critical"  # frequencies, runway length / heading, ILS category
    HIGH = "high"          # elevation, coordinates, magnetic variation, surface
    NORMAL = "normal"      # operator, city, region, operating hours, type
    LOW = "low"            # freetext remarks, secondary notes


# Product decision 2026-04-20: pipeline uses exclusively Claude + OpenAI as
# vision extractors. Tesseract is used SEPARATELY as a grounding check,
# NOT as a vote. Consensus therefore needs 2-of-2 LLM agreement across all
# risk classes; the grounding check is an orthogonal hard gate applied by
# the orchestrator (see `parser.grounding`).
MIN_SOURCES_FOR_CONSENSUS: dict[RiskClass, int] = {
    RiskClass.CRITICAL: 2,
    RiskClass.HIGH: 2,
    RiskClass.NORMAL: 2,
    RiskClass.LOW: 1,
}


class SourceKind(str, Enum):
    LLM_A = "llm_a"          # Claude Vision
    LLM_B = "llm_b"          # OpenAI Vision (GPT-4o)


@dataclass
class SourceVote:
    kind: SourceKind
    value: Any
    # Optional metadata — not used in equality, carried into audit.
    bbox: tuple[int, int, int, int] | None = None
    raw_response: Any = None
    model_version: str | None = None


@dataclass
class ConsensusDecision:
    """Result of `reach_consensus`. Never mutates inputs."""

    persisted_value: Any | None
    """The value that may be written to the main table. `None` = fail-closed."""

    result: str
    """One of:
       - accepted_html_anchored
       - accepted_3_of_3
       - accepted_2_of_3
       - accepted_single_source   (only for LOW)
       - rejected_disagreement
       - rejected_domain
       - rejected_unit_parse
       - rejected_insufficient_sources
       - pending_human_review     (CRITICAL with disagreement)
    """

    contributing_sources: list[SourceKind] = field(default_factory=list)
    """Sources that actually agreed on the persisted value."""

    rejected_sources: list[SourceKind] = field(default_factory=list)
    """Sources that disagreed with the winning value (or could not be parsed)."""

    needs_human_review: bool = False
    error_note: str | None = None


def reach_consensus(
    *,
    field: str,
    risk: RiskClass,
    votes: list[SourceVote],
    domain_validator=None,
) -> ConsensusDecision:
    """Combine N source votes into a single persist-or-not decision.

    `domain_validator` is an optional callable `(value) -> value | raises ValidationError`
    applied after normalization. Caller injects the right validator per field.
    """
    # 1) Normalize every non-null vote. Track parse failures as implicit rejects.
    normalized: list[tuple[SourceKind, Any, SourceVote]] = []
    parse_failed: list[SourceKind] = []
    for v in votes:
        if v.value is None:
            continue
        try:
            nv = normalize(field, v.value)
        except UnitError:
            parse_failed.append(v.kind)
            continue
        if nv is None or (isinstance(nv, str) and nv == ""):
            continue
        normalized.append((v.kind, nv, v))

    if not normalized:
        return ConsensusDecision(
            persisted_value=None,
            result="rejected_insufficient_sources",
            rejected_sources=parse_failed,
            needs_human_review=(risk is RiskClass.CRITICAL),
        )

    # 2) Group by normalized value (using hashable stringified form for safety).
    groups: dict[str, list[SourceKind]] = {}
    value_by_key: dict[str, Any] = {}
    for kind, nv, _ in normalized:
        key = _hashable(nv)
        groups.setdefault(key, []).append(kind)
        value_by_key[key] = nv

    # 3) Plain majority, constrained by risk class.
    # (HTML-anchor branch removed 2026-04-20 per product decision — pipeline
    # uses exclusively Claude + OpenAI vision; grounding is handled
    # orthogonally by `parser.grounding`.)
    best_key = max(groups, key=lambda k: len(groups[k]))
    best_count = len(groups[best_key])
    best_value = value_by_key[best_key]

    required = MIN_SOURCES_FOR_CONSENSUS[risk]
    if best_count < required:
        return ConsensusDecision(
            persisted_value=None,
            result="rejected_insufficient_sources"
            if len(normalized) < required
            else "rejected_disagreement",
            rejected_sources=[k for k, _, _ in normalized] + parse_failed,
            needs_human_review=(risk is RiskClass.CRITICAL),
        )

    # 5) Domain validation.
    if not _passes_domain(best_value, domain_validator):
        return ConsensusDecision(
            persisted_value=None,
            result="rejected_domain",
            contributing_sources=groups[best_key],
            rejected_sources=[
                k for k in [v[0] for v in normalized] if k not in groups[best_key]
            ] + parse_failed,
            needs_human_review=(risk is RiskClass.CRITICAL),
            error_note="consensus reached but value failed domain constraints",
        )

    winners = groups[best_key]
    result_label = (
        "accepted_3_of_3" if best_count >= 3
        else "accepted_2_of_3" if best_count >= 2
        else "accepted_single_source"
    )

    return ConsensusDecision(
        persisted_value=best_value,
        result=result_label,
        contributing_sources=winners,
        rejected_sources=[
            k for k, _, _ in normalized if k not in winners
        ] + parse_failed,
    )


def _passes_domain(value: Any, validator) -> bool:
    if validator is None:
        return True
    try:
        validator(value)
    except ValidationError:
        return False
    return True


def _hashable(value: Any) -> str:
    """Convert a normalized value to a deterministic string key for grouping."""
    if value is None:
        return "<null>"
    if isinstance(value, float):
        # Avoid float-equality pitfalls by rounding to 6 dp for grouping.
        return f"{value:.6f}"
    return str(value)
