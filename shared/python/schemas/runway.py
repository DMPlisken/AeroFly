"""Runway — physical runway, with low-end (LE) and high-end (HE) designators."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .enums import RunwaySurface


class RunwayBase(BaseModel):
    aerodrome_icao: str = Field(pattern=r"^[A-Z]{4}$")
    designator_le: str = Field(description="Low-end designator, e.g. '08L', '07'")
    designator_he: str = Field(description="High-end designator, e.g. '26R', '25'")
    true_heading_le: Decimal | None = Field(default=None, description="LE true heading in degrees")
    true_heading_he: Decimal | None = None
    length_m: int | None = None
    width_m: int | None = None
    surface: RunwaySurface = RunwaySurface.OTHER
    strength: str | None = Field(default=None, description="PCN / MTOW limit, free text")
    le_thr_elevation_ft: int | None = None
    he_thr_elevation_ft: int | None = None
    # Declared distances (ICAO AIP AD 2.13)
    le_tora_m: int | None = None
    le_toda_m: int | None = None
    le_asda_m: int | None = None
    le_lda_m: int | None = None
    he_tora_m: int | None = None
    he_toda_m: int | None = None
    he_asda_m: int | None = None
    he_lda_m: int | None = None
    ils_le: bool = False
    ils_he: bool = False
    remark: str | None = None
    remark_de: str | None = None
    source_airac_cycle: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")


class RunwayCreate(RunwayBase):
    pass


class Runway(RunwayBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
