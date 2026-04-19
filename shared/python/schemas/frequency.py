"""Frequency — communications frequency assigned to an aerodrome service."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .enums import FrequencyType


class FrequencyBase(BaseModel):
    aerodrome_icao: str = Field(pattern=r"^[A-Z]{4}$")
    type: FrequencyType
    callsign: str | None = None
    callsign_de: str | None = None
    frequency_mhz: Decimal = Field(ge=Decimal("108.000"), le=Decimal("137.000"))
    remark: str | None = None
    remark_de: str | None = None
    operational_hours: str | None = Field(
        default=None, description="Free-form schedule, e.g. 'MON-FRI 0600-2200 (SR-SS local)'"
    )
    operational_hours_de: str | None = None
    source_airac_cycle: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")


class FrequencyCreate(FrequencyBase):
    pass


class Frequency(FrequencyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
