"""Aerodrome — top-level entity. Natural PK is ICAO code."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .enums import AerodromeType


class AerodromeBase(BaseModel):
    icao: str = Field(pattern=r"^[A-Z]{4}$", description="ICAO code, e.g. 'EDDM'")
    iata: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    name: str = Field(description="Official English name")
    name_de: str | None = Field(default=None, description="German name")
    city: str | None = None
    city_de: str | None = None
    region: str | None = None
    region_de: str | None = None
    country: str = Field(default="DE", pattern=r"^[A-Z]{2}$", description="ISO 3166-1 alpha-2")
    type: AerodromeType = AerodromeType.OTHER
    operator: str | None = None
    operator_de: str | None = None
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    elevation_ft: int | None = None
    magnetic_variation: Decimal | None = Field(default=None, description="Degrees; W negative, E positive")
    ref_point_remark: str | None = None
    ref_point_remark_de: str | None = None
    source_airac_cycle: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")


class AerodromeCreate(AerodromeBase):
    pass


class AerodromeUpdate(BaseModel):
    """Partial update — all fields optional."""
    name: str | None = None
    name_de: str | None = None
    city: str | None = None
    city_de: str | None = None
    region: str | None = None
    region_de: str | None = None
    type: AerodromeType | None = None
    operator: str | None = None
    operator_de: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    elevation_ft: int | None = None
    magnetic_variation: Decimal | None = None
    ref_point_remark: str | None = None
    ref_point_remark_de: str | None = None
    source_airac_cycle: str | None = None


class Aerodrome(AerodromeBase):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    updated_at: datetime
