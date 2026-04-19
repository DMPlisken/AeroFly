"""Pydantic response schemas for LLM extraction.

Every provider MUST return these shapes. The LLM prompt embeds the JSON
schema and the structured-output feature of the provider enforces it.

Bounding boxes are pixel coordinates `[x0, y0, x1, y1]` in the PNG's own
frame (provider sees the raw bytes; its bbox is over the input image).
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


BBox = tuple[int, int, int, int]


class ExtractedValue[T](BaseModel):
    """Generic wrapper — a single value with its bbox.

    If the provider could not read the value confidently, it MUST set
    `value=None` — never guess.
    """

    model_config = ConfigDict(extra="forbid")

    value: T | None = None
    bbox: BBox | None = None
    note: str | None = Field(
        default=None,
        description="Free-text note from the model, e.g. 'partially occluded'",
    )


class GeoExtraction(BaseModel):
    """AD 2.2 — Aerodrome geographical and administrative data."""

    model_config = ConfigDict(extra="forbid")

    latitude_deg: ExtractedValue[float] | None = None
    longitude_deg: ExtractedValue[float] | None = None
    elevation_ft: ExtractedValue[int] | None = None
    magnetic_variation_deg: ExtractedValue[Decimal] | None = None
    reference_temp_c: ExtractedValue[Decimal] | None = None
    operator: ExtractedValue[str] | None = None
    operator_de: ExtractedValue[str] | None = None
    city: ExtractedValue[str] | None = None
    city_de: ExtractedValue[str] | None = None


class RunwayExtraction(BaseModel):
    """AD 2.12 — Physical characteristics of one runway."""

    model_config = ConfigDict(extra="forbid")

    designator_le: ExtractedValue[str]
    designator_he: ExtractedValue[str]
    true_heading_le_deg: ExtractedValue[Decimal] | None = None
    true_heading_he_deg: ExtractedValue[Decimal] | None = None
    length_m: ExtractedValue[int] | None = None
    width_m: ExtractedValue[int] | None = None
    surface: ExtractedValue[str] | None = None
    ils_le: ExtractedValue[bool] | None = None
    ils_he: ExtractedValue[bool] | None = None


class RunwaysExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    runways: list[RunwayExtraction] = Field(default_factory=list)


class FrequencyExtraction(BaseModel):
    """AD 2.18 — ATS communication facility."""

    model_config = ConfigDict(extra="forbid")

    type: ExtractedValue[str]     # canonical enum: twr, gnd, atis, …
    callsign: ExtractedValue[str] | None = None
    callsign_de: ExtractedValue[str] | None = None
    frequency_mhz: ExtractedValue[Decimal]
    operational_hours: ExtractedValue[str] | None = None


class FrequenciesExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    frequencies: list[FrequencyExtraction] = Field(default_factory=list)
