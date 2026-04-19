"""Chart — PDF/image document scraped from DFS AIP for an aerodrome."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import ChartType


class ChartBase(BaseModel):
    aerodrome_icao: str = Field(pattern=r"^[A-Z]{4}$")
    chart_type: ChartType
    title: str
    title_de: str | None = None
    source_url: str = Field(description="DFS source URL (unique)")
    local_path: str | None = Field(default=None, description="Relative path within the media store")
    content_hash: str | None = Field(default=None, description="SHA-256 of the file bytes")
    file_size_bytes: int | None = None
    page_count: int | None = None
    language: str = Field(default="de", pattern=r"^(de|en)$")
    source_airac_cycle: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")


class ChartCreate(ChartBase):
    pass


class Chart(ChartBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
