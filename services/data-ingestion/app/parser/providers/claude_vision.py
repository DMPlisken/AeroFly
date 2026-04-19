"""Claude Vision extraction provider.

Loads lazily — only when first called. Requires `ANTHROPIC_API_KEY` env var.
Uses structured output (tool use) to guarantee JSON shape.

NOT YET WIRED TO REAL API CALLS. This file is the skeleton; the actual
`anthropic` SDK call is added after Gate α (user approval of spike).
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import ExtractionProvider, FieldGroup, ProviderNotConfigured, ProviderResult


class ClaudeVisionProvider(ExtractionProvider):
    name = "claude-vision"

    # Locked to a specific model version for reproducibility — ANY upgrade
    # goes through the canary process described in the plan §16.
    MODEL_ID = "claude-sonnet-4-6-20250929"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None  # lazy — don't construct until used

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def extract(self, *, image_path: Path, field_group: FieldGroup) -> ProviderResult:
        if not self.is_configured():
            raise ProviderNotConfigured(
                "ANTHROPIC_API_KEY is not set — Claude Vision is unavailable. "
                "Set it in .env before running the spike."
            )
        # Deliberately unimplemented until Gate α — see plan.
        raise NotImplementedError(
            "Claude Vision call is deferred until Gate α (see the plan). "
            "Activate by implementing the anthropic SDK call here when the "
            "spike is approved."
        )
