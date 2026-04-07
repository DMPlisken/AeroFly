"""Shared aerodrome schemas used across services."""

from pydantic import BaseModel


class AerodromeBase(BaseModel):
    icao_code: str
    name: str
    name_de: str | None = None
    city: str | None = None
    state: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    elevation_ft: int | None = None
