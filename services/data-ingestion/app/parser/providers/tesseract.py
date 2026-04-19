"""Tesseract OCR provider — independent third source.

Tesseract runs locally (no API key needed) but the tesseract binary must
be installed in the container (apt: `tesseract-ocr`). Tesseract is
deliberately narrow: given a bbox from the LLMs, it OCRs ONLY that
region. This prevents independent positional halluczinations.

Left as a skeleton — real pytesseract integration goes in once the
Dockerfile is updated in Phase 0 spike-run.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .base import ExtractionProvider, FieldGroup, ProviderNotConfigured, ProviderResult


class TesseractProvider(ExtractionProvider):
    name = "tesseract"

    def is_configured(self) -> bool:
        return shutil.which("tesseract") is not None

    def extract(self, *, image_path: Path, field_group: FieldGroup) -> ProviderResult:
        if not self.is_configured():
            raise ProviderNotConfigured(
                "`tesseract` binary not found on PATH. Install with: "
                "apt-get install tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng"
            )
        raise NotImplementedError(
            "Tesseract integration is deferred until Gate α. "
            "Will consume bboxes returned by the LLM providers and OCR only those crops."
        )
