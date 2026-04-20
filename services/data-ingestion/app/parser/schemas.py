"""Pydantic response schemas for LLM extraction (VFR scope).

Every provider MUST return these shapes. The LLM prompt embeds the JSON
schema and the structured-output feature of the provider enforces it.

Bounding boxes are pixel coordinates `[x0, y0, x1, y1]` in the PNG's own
frame (provider sees the raw bytes; its bbox is over the input image).

Scope: what's printed on German VFR charts (VAC / ADC). IFR-only fields
that are never on VFR charts (reference temperature, annual MAGVAR
change, per-end ILS, detailed declared distances, true headings) are
kept in the DB schema but not requested from the LLM — they'd always be
null and waste tokens.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

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
    """Aerodrome geographical and administrative data (VFR chart header/box)."""

    model_config = ConfigDict(extra="forbid")

    latitude_deg: ExtractedValue[float] | None = None
    longitude_deg: ExtractedValue[float] | None = None
    elevation_ft: ExtractedValue[int] | None = None
    magnetic_variation_deg: ExtractedValue[Decimal] | None = None
    operator: ExtractedValue[str] | None = None
    operator_de: ExtractedValue[str] | None = None
    city: ExtractedValue[str] | None = None
    city_de: ExtractedValue[str] | None = None


class RunwayExtraction(BaseModel):
    """Physical characteristics of one runway on a VFR chart."""

    model_config = ConfigDict(extra="forbid")

    designator_le: ExtractedValue[str]
    designator_he: ExtractedValue[str]
    length_m: ExtractedValue[int] | None = None
    width_m: ExtractedValue[int] | None = None
    surface: ExtractedValue[str] | None = None
    traffic_pattern_altitude_ft: ExtractedValue[int] | None = None
    traffic_pattern_side: ExtractedValue[Literal["left", "right"]] | None = None


class RunwaysExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    runways: list[RunwayExtraction] = Field(default_factory=list)


class FrequencyExtraction(BaseModel):
    """One ATS communication facility from a VFR chart's frequency box."""

    model_config = ConfigDict(extra="forbid")

    type: ExtractedValue[str]     # canonical enum: twr, gnd, atis, info, …
    callsign: ExtractedValue[str] | None = None
    callsign_de: ExtractedValue[str] | None = None
    frequency_mhz: ExtractedValue[Decimal]
    operational_hours: ExtractedValue[str] | None = None


class FrequenciesExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    frequencies: list[FrequencyExtraction] = Field(default_factory=list)


class ObstacleExtraction(BaseModel):
    """A charted obstacle — mast, tower, terrain peak, building."""

    model_config = ConfigDict(extra="forbid")

    description: ExtractedValue[str] | None = None
    description_de: ExtractedValue[str] | None = None
    latitude_deg: ExtractedValue[float] | None = None
    longitude_deg: ExtractedValue[float] | None = None
    elevation_ft: ExtractedValue[int] | None = None  # AMSL height of obstacle top
    height_ft: ExtractedValue[int] | None = None     # AGL height
    lighted: ExtractedValue[bool] | None = None


class ObstaclesExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    obstacles: list[ObstacleExtraction] = Field(default_factory=list)


class ReportingPointExtraction(BaseModel):
    """A VFR reporting point — e.g. 'November', 'Echo'."""

    model_config = ConfigDict(extra="forbid")

    name: ExtractedValue[str]
    type: ExtractedValue[Literal["compulsory", "non_compulsory"]] | None = None
    latitude_deg: ExtractedValue[float] | None = None
    longitude_deg: ExtractedValue[float] | None = None


class ReportingPointsExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reporting_points: list[ReportingPointExtraction] = Field(default_factory=list)
