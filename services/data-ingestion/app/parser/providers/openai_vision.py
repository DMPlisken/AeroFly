"""OpenAI Vision (GPT-4o) extraction provider — second independent source.

Loads lazily — only when first called. Requires `OPENAI_API_KEY` env var.
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import ExtractionProvider, FieldGroup, ProviderNotConfigured, ProviderResult


class OpenAIVisionProvider(ExtractionProvider):
    name = "openai-vision"

    MODEL_ID = "gpt-4o-2024-11-20"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def extract(self, *, image_path: Path, field_group: FieldGroup) -> ProviderResult:
        if not self.is_configured():
            raise ProviderNotConfigured(
                "OPENAI_API_KEY is not set — GPT-4o Vision is unavailable. "
                "Set it in .env before running the spike."
            )
        raise NotImplementedError(
            "OpenAI Vision call is deferred until Gate α (see the plan)."
        )
