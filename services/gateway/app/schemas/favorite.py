"""Pydantic schemas for favorite endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FavoriteCreate(BaseModel):
    """Payload for POST /api/favorites."""

    icao: str = Field(
        ...,
        min_length=3,
        max_length=8,
        description="ICAO code of the aerodrome to mark as favorite (e.g. 'EDDF').",
    )

    @field_validator("icao")
    @classmethod
    def normalize_icao(cls, value: str) -> str:
        return value.strip().upper()


class FavoriteOut(BaseModel):
    """Single favorite returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    icao: str
    created_at: datetime
