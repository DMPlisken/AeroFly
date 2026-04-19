"""Abstract base class for all extraction providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


class ProviderNotConfigured(RuntimeError):
    """Raised when a provider is called but its API key / binary is missing.

    Callers MUST catch this and treat the provider as absent from the vote.
    A missing provider is never an error — it just reduces the number of
    available sources for consensus.
    """


FieldGroup = Literal["geo", "runways", "frequencies"]


@dataclass
class ProviderResult:
    """Output from a single provider call.

    - `raw_response`: the untruncated original JSON for the audit trail.
    - `parsed`: Pydantic-validated shape (one of the schemas).
    - `model_version`: exact version string for reproducibility.
    - `prompt_version`: version string matching `parser.prompts`.
    - `input_image_sha256`: hash of the PNG bytes actually sent.
    """

    raw_response: dict[str, Any]
    parsed: Any
    model_version: str
    prompt_version: str
    input_image_sha256: str


class ExtractionProvider(ABC):
    """Base class for LLM or OCR providers."""

    #: machine-readable provider identifier, e.g. "claude-vision"
    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True iff the provider has the credentials / binaries it needs."""

    @abstractmethod
    def extract(
        self,
        *,
        image_path: Path,
        field_group: FieldGroup,
    ) -> ProviderResult:
        """Run extraction on an image for one field group.

        Raises `ProviderNotConfigured` if credentials are missing.
        """
