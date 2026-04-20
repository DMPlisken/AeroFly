"""Published token pricing for each supported model.

All values are USD per 1_000_000 tokens. Every entry is traceable to the
vendor's pricing page on the date noted; update as part of a conscious
review, never silently.

If a model is used that is not listed here, pricing fields will be 0.00 —
the call is still recorded so the cost can be back-filled later.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TypedDict


class ModelRates(TypedDict):
    input: Decimal
    output: Decimal
    cached_input: Decimal
    cache_creation: Decimal
    source_url: str
    fetched_at: str


# Source: https://www.anthropic.com/pricing as of 2026-04-20
# Source: https://openai.com/api/pricing as of 2026-04-20
#
# Anthropic prompt caching: cache-writes cost 25 % more than base input;
# cache-reads cost 10 % of base input.
# OpenAI prompt caching: cache-reads cost 50 % of base input (no write fee).
PRICING: dict[str, ModelRates] = {
    "claude-sonnet-4-6": {
        "input": Decimal("3.00"),
        "output": Decimal("15.00"),
        "cached_input": Decimal("0.30"),
        "cache_creation": Decimal("3.75"),
        "source_url": "https://www.anthropic.com/pricing",
        "fetched_at": "2026-04-20",
    },
    "gpt-4o-2024-11-20": {
        "input": Decimal("2.50"),
        "output": Decimal("10.00"),
        "cached_input": Decimal("1.25"),
        "cache_creation": Decimal("0"),  # OpenAI has no separate write fee
        "source_url": "https://openai.com/api/pricing",
        "fetched_at": "2026-04-20",
    },
}

MILLION = Decimal("1000000")


def rates_for(model: str) -> ModelRates | None:
    return PRICING.get(model)


def cost_for_tokens(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
    cache_creation_tokens: int = 0,
) -> dict[str, Decimal]:
    """Compute per-call cost components. Returns zero-valued dict for unknown models."""
    rates = PRICING.get(model)
    if rates is None:
        return {
            "input_cost_usd": Decimal("0"),
            "output_cost_usd": Decimal("0"),
            "cached_input_cost_usd": Decimal("0"),
            "cache_creation_cost_usd": Decimal("0"),
            "total_cost_usd": Decimal("0"),
        }

    input_cost = (Decimal(input_tokens) * rates["input"]) / MILLION
    output_cost = (Decimal(output_tokens) * rates["output"]) / MILLION
    cached_cost = (Decimal(cached_input_tokens) * rates["cached_input"]) / MILLION
    creation_cost = (Decimal(cache_creation_tokens) * rates["cache_creation"]) / MILLION
    total = input_cost + output_cost + cached_cost + creation_cost

    return {
        "input_cost_usd": input_cost.quantize(Decimal("0.000001")),
        "output_cost_usd": output_cost.quantize(Decimal("0.000001")),
        "cached_input_cost_usd": cached_cost.quantize(Decimal("0.000001")),
        "cache_creation_cost_usd": creation_cost.quantize(Decimal("0.000001")),
        "total_cost_usd": total.quantize(Decimal("0.000001")),
    }
