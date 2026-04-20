"""Tests that both vision providers retry once after an image-size rejection.

These tests do not hit real APIs. They replace the provider's `_call_api`
method with a scripted sequence of fake responses / exceptions, and
verify the retry wiring + audit-row recording.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest
from PIL import Image

from app.parser.providers.claude_vision import ClaudeVisionProvider
from app.parser.providers.openai_vision import OpenAIVisionProvider
from app.parser.usage_tracker import UsageRecord


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeTracker:
    """Collects UsageRecord calls instead of persisting them."""

    def __init__(self) -> None:
        self.records: list[UsageRecord] = []

    def record(self, usage: UsageRecord) -> int | None:
        self.records.append(usage)
        return len(self.records)


# -- Claude response shape --

@dataclass
class _ClaudeUsage:
    input_tokens: int = 1000
    output_tokens: int = 50
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class _ClaudeBlock:
    type: str
    text: str


@dataclass
class _ClaudeResponse:
    id: str = "msg_fake"
    usage: _ClaudeUsage = None
    content: list = None

    def __post_init__(self):
        if self.usage is None:
            self.usage = _ClaudeUsage()
        if self.content is None:
            self.content = [_ClaudeBlock(type="text", text='{"latitude_deg": null}')]


# -- OpenAI response shape --

@dataclass
class _OpenAIDetails:
    cached_tokens: int = 0


@dataclass
class _OpenAIUsage:
    prompt_tokens: int = 1000
    completion_tokens: int = 50
    prompt_tokens_details: _OpenAIDetails = None

    def __post_init__(self):
        if self.prompt_tokens_details is None:
            self.prompt_tokens_details = _OpenAIDetails()


@dataclass
class _OpenAIMessage:
    content: str = '{"latitude_deg": null}'


@dataclass
class _OpenAIChoice:
    message: _OpenAIMessage = None

    def __post_init__(self):
        if self.message is None:
            self.message = _OpenAIMessage()


@dataclass
class _OpenAIResponse:
    id: str = "chatcmpl_fake"
    usage: _OpenAIUsage = None
    choices: list = None

    def __post_init__(self):
        if self.usage is None:
            self.usage = _OpenAIUsage()
        if self.choices is None:
            self.choices = [_OpenAIChoice()]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_oversized_png(tmp_path: Path) -> Path:
    img = Image.new("RGB", (3000, 2000), (10, 10, 10))
    path = tmp_path / "oversized.png"
    img.save(path, format="PNG")
    return path


def _write_small_png(tmp_path: Path) -> Path:
    img = Image.new("RGB", (100, 100), (10, 10, 10))
    path = tmp_path / "small.png"
    img.save(path, format="PNG")
    return path


def _scripted(sequence: list):
    """Return a callable that yields the next item on each call.

    Items that are Exception instances are raised; everything else is returned.
    """
    it = iter(sequence)

    def _call(*args, **kwargs):
        item = next(it)
        if isinstance(item, BaseException):
            raise item
        return item

    return _call


# ---------------------------------------------------------------------------
# Claude provider tests
# ---------------------------------------------------------------------------

def test_claude_success_first_try_records_one_success(tmp_path, monkeypatch):
    tracker = FakeTracker()
    provider = ClaudeVisionProvider(api_key="fake-key", tracker=tracker)
    monkeypatch.setattr(provider, "_call_api", _scripted([_ClaudeResponse()]))

    result = provider.extract(
        image_path=_write_small_png(tmp_path),
        field_group="geo",
        aerodrome_icao="EDDM",
    )
    assert result.model_version == ClaudeVisionProvider.MODEL_ID
    assert len(tracker.records) == 1
    assert tracker.records[0].success is True


def test_claude_size_error_triggers_downscale_and_retry(tmp_path, monkeypatch):
    tracker = FakeTracker()
    provider = ClaudeVisionProvider(api_key="fake-key", tracker=tracker)
    monkeypatch.setattr(
        provider,
        "_call_api",
        _scripted([
            ValueError("image too large: exceeds 8000x8000 pixels"),
            _ClaudeResponse(),
        ]),
    )

    result = provider.extract(
        image_path=_write_oversized_png(tmp_path),
        field_group="geo",
        aerodrome_icao="EDDM",
    )
    assert result.model_version == ClaudeVisionProvider.MODEL_ID
    # Two audit rows: the oversize failure + the retry success.
    assert len(tracker.records) == 2
    assert tracker.records[0].success is False
    assert tracker.records[0].error_code == "image_size_rejected"
    assert tracker.records[1].success is True


def test_claude_non_size_error_does_not_retry(tmp_path, monkeypatch):
    tracker = FakeTracker()
    provider = ClaudeVisionProvider(api_key="fake-key", tracker=tracker)
    monkeypatch.setattr(
        provider,
        "_call_api",
        _scripted([RuntimeError("rate limit exceeded")]),
    )

    with pytest.raises(RuntimeError, match="rate limit"):
        provider.extract(
            image_path=_write_small_png(tmp_path),
            field_group="geo",
        )
    # One audit row, the generic failure. No retry row.
    assert len(tracker.records) == 1
    assert tracker.records[0].success is False
    assert tracker.records[0].error_code == "RuntimeError"


def test_claude_size_error_but_already_small_raises(tmp_path, monkeypatch):
    """Provider claims size error but image is within bounds — no safe retry."""
    tracker = FakeTracker()
    provider = ClaudeVisionProvider(api_key="fake-key", tracker=tracker)
    monkeypatch.setattr(
        provider,
        "_call_api",
        _scripted([ValueError("image size exceeds maximum")]),
    )

    with pytest.raises(ValueError, match="image size"):
        provider.extract(
            image_path=_write_small_png(tmp_path),  # already small
            field_group="geo",
        )
    # First-failure row was recorded before the downscale short-circuited.
    # Then the outer except records a second failure row with the exc type.
    assert len(tracker.records) == 2
    assert tracker.records[0].error_code == "image_size_rejected"
    assert tracker.records[1].error_code == "ValueError"


# ---------------------------------------------------------------------------
# OpenAI provider tests (symmetric wiring; same expectations)
# ---------------------------------------------------------------------------

def test_openai_success_first_try_records_one_success(tmp_path, monkeypatch):
    tracker = FakeTracker()
    provider = OpenAIVisionProvider(api_key="fake-key", tracker=tracker)
    monkeypatch.setattr(provider, "_call_api", _scripted([_OpenAIResponse()]))

    result = provider.extract(
        image_path=_write_small_png(tmp_path),
        field_group="geo",
        aerodrome_icao="EDDM",
    )
    assert result.model_version == OpenAIVisionProvider.MODEL_ID
    assert len(tracker.records) == 1
    assert tracker.records[0].success is True


def test_openai_size_error_triggers_downscale_and_retry(tmp_path, monkeypatch):
    tracker = FakeTracker()
    provider = OpenAIVisionProvider(api_key="fake-key", tracker=tracker)
    monkeypatch.setattr(
        provider,
        "_call_api",
        _scripted([
            ValueError("image dimensions exceed 4096 pixels"),
            _OpenAIResponse(),
        ]),
    )

    result = provider.extract(
        image_path=_write_oversized_png(tmp_path),
        field_group="geo",
        aerodrome_icao="EDDM",
    )
    assert result.model_version == OpenAIVisionProvider.MODEL_ID
    assert len(tracker.records) == 2
    assert tracker.records[0].success is False
    assert tracker.records[0].error_code == "image_size_rejected"
    assert tracker.records[1].success is True


def test_openai_non_size_error_does_not_retry(tmp_path, monkeypatch):
    tracker = FakeTracker()
    provider = OpenAIVisionProvider(api_key="fake-key", tracker=tracker)
    monkeypatch.setattr(
        provider,
        "_call_api",
        _scripted([RuntimeError("rate limit exceeded")]),
    )

    with pytest.raises(RuntimeError, match="rate limit"):
        provider.extract(
            image_path=_write_small_png(tmp_path),
            field_group="geo",
        )
    assert len(tracker.records) == 1
    assert tracker.records[0].error_code == "RuntimeError"
