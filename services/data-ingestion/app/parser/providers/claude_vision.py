"""Claude Vision extraction provider (real SDK)."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from pathlib import Path

from ..prompts import load as load_prompt
from ..usage_tracker import UsageRecord, UsageTracker
from .base import ExtractionProvider, FieldGroup, ProviderNotConfigured, ProviderResult


class ClaudeVisionProvider(ExtractionProvider):
    name = "claude-vision"

    # Locked version. Upgrades go through the canary process documented in §16.
    MODEL_ID = "claude-sonnet-4-6"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        tracker: UsageTracker | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.tracker = tracker
        self._client = None

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def extract(
        self,
        *,
        image_path: Path,
        field_group: FieldGroup,
        aerodrome_icao: str | None = None,
        source_chart_id: int | None = None,
    ) -> ProviderResult:
        if not self.is_configured():
            raise ProviderNotConfigured("ANTHROPIC_API_KEY is not set")

        prompt_version, prompt_text = load_prompt(field_group)

        image_bytes = image_path.read_bytes()
        image_hash = hashlib.sha256(image_bytes).hexdigest()
        image_b64 = base64.standard_b64encode(image_bytes).decode()

        client = self._get_client()
        start = time.monotonic()
        request_id: str | None = None
        try:
            # Prompt caching: the system prompt is identical across every
            # aerodrome for a given field group. Marking it `ephemeral`
            # lets Anthropic charge 10 % of the base rate on cache hits
            # (5 min TTL) — massively reduces cost of a batch run.
            response = client.messages.create(
                model=self.MODEL_ID,
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": prompt_text,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": "Return ONLY the JSON object matching the described schema.",
                            },
                        ],
                    }
                ],
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            request_id = getattr(response, "id", None)

            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "input_tokens", 0) if usage else 0
            output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
            cached_input = getattr(usage, "cache_read_input_tokens", 0) if usage else 0
            cache_creation = getattr(usage, "cache_creation_input_tokens", 0) if usage else 0

            if self.tracker is not None:
                self.tracker.record(UsageRecord(
                    provider="claude",
                    model=self.MODEL_ID,
                    purpose=f"extract:{field_group}",
                    aerodrome_icao=aerodrome_icao,
                    source_chart_id=source_chart_id,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cached_input_tokens=cached_input,
                    cache_creation_tokens=cache_creation,
                    latency_ms=latency_ms,
                    success=True,
                    request_id=request_id,
                ))

            text_blocks = [b.text for b in response.content if getattr(b, "type", "") == "text"]
            raw_text = "\n".join(text_blocks).strip()
            parsed = _extract_json(raw_text)

            return ProviderResult(
                raw_response={
                    "text": raw_text,
                    "parsed": parsed,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cached_input_tokens": cached_input,
                        "cache_creation_tokens": cache_creation,
                    },
                },
                parsed=parsed,
                model_version=self.MODEL_ID,
                prompt_version=prompt_version,
                input_image_sha256=image_hash,
            )
        except Exception as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            if self.tracker is not None:
                self.tracker.record(UsageRecord(
                    provider="claude",
                    model=self.MODEL_ID,
                    purpose=f"extract:{field_group}",
                    aerodrome_icao=aerodrome_icao,
                    source_chart_id=source_chart_id,
                    latency_ms=latency_ms,
                    success=False,
                    error_code=type(exc).__name__,
                    request_id=request_id,
                ))
            raise


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
