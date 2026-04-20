"""OpenAI Vision (GPT-4o) extraction provider — second independent source."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import time
from pathlib import Path

from ..image_guard import downscale_png, is_image_size_error
from ..prompts import load as load_prompt
from ..usage_tracker import UsageRecord, UsageTracker
from .base import ExtractionProvider, FieldGroup, ProviderNotConfigured, ProviderResult

log = logging.getLogger(__name__)


class OpenAIVisionProvider(ExtractionProvider):
    name = "openai-vision"

    MODEL_ID = "gpt-4o-2024-11-20"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        tracker: UsageTracker | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.tracker = tracker
        self._client = None

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def _call_api(self, image_b64: str, prompt_text: str):
        client = self._get_client()
        return client.chat.completions.create(
            model=self.MODEL_ID,
            max_tokens=4096,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt_text},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                        {
                            "type": "text",
                            "text": "Return ONLY the JSON object matching the described schema.",
                        },
                    ],
                },
            ],
        )

    def extract(
        self,
        *,
        image_path: Path,
        field_group: FieldGroup,
        aerodrome_icao: str | None = None,
        source_chart_id: int | None = None,
    ) -> ProviderResult:
        if not self.is_configured():
            raise ProviderNotConfigured("OPENAI_API_KEY is not set")

        prompt_version, prompt_text = load_prompt(field_group)

        image_bytes = image_path.read_bytes()
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        request_id: str | None = None
        start = time.monotonic()
        try:
            # Attempt 1: send as stored on disk.
            try:
                response = self._call_api(
                    base64.standard_b64encode(image_bytes).decode(),
                    prompt_text,
                )
            except Exception as exc:
                if not is_image_size_error(exc):
                    raise

                first_latency = int((time.monotonic() - start) * 1000)
                if self.tracker is not None:
                    self.tracker.record(UsageRecord(
                        provider="openai",
                        model=self.MODEL_ID,
                        purpose=f"extract:{field_group}",
                        aerodrome_icao=aerodrome_icao,
                        source_chart_id=source_chart_id,
                        latency_ms=first_latency,
                        success=False,
                        error_code="image_size_rejected",
                    ))

                ds = downscale_png(image_bytes)
                if ds.new_size is None:
                    raise
                log.warning(
                    "openai: retrying %s after downscale %s -> %s",
                    image_path.name, ds.original_size, ds.new_size,
                )
                start = time.monotonic()
                response = self._call_api(
                    base64.standard_b64encode(ds.png_bytes).decode(),
                    prompt_text,
                )

            latency_ms = int((time.monotonic() - start) * 1000)
            request_id = getattr(response, "id", None)

            usage = getattr(response, "usage", None)
            input_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            output_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

            # OpenAI returns prompt_tokens_details with cached_tokens when caching triggers.
            cached_input = 0
            if usage is not None:
                details = getattr(usage, "prompt_tokens_details", None)
                if details is not None:
                    cached_input = getattr(details, "cached_tokens", 0) or 0

            if self.tracker is not None:
                self.tracker.record(UsageRecord(
                    provider="openai",
                    model=self.MODEL_ID,
                    purpose=f"extract:{field_group}",
                    aerodrome_icao=aerodrome_icao,
                    source_chart_id=source_chart_id,
                    input_tokens=input_tokens - cached_input,  # uncached
                    output_tokens=output_tokens,
                    cached_input_tokens=cached_input,
                    latency_ms=latency_ms,
                    success=True,
                    request_id=request_id,
                ))

            raw_text = response.choices[0].message.content or ""
            parsed = json.loads(raw_text)

            return ProviderResult(
                raw_response={
                    "text": raw_text,
                    "parsed": parsed,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cached_input_tokens": cached_input,
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
                    provider="openai",
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
