"""Extraction providers — abstract base + concrete implementations.

All providers return the same Pydantic shapes (see `parser.schemas`) so the
consensus engine can compare them source-by-source.
"""

from .base import ExtractionProvider, ProviderNotConfigured, ProviderResult

__all__ = ["ExtractionProvider", "ProviderNotConfigured", "ProviderResult"]
