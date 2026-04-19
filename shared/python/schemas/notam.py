"""NOTAM — Notice to Airmen, structured per ICAO Annex 15 Appendix 6."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import NotamCategory, NotamPurpose, NotamScope, NotamSeverity, NotamTraffic


class NotamBase(BaseModel):
    notam_id: str = Field(description="NOTAM number, e.g. 'A5543/26'")
    aerodrome_icao: str | None = Field(default=None, pattern=r"^[A-Z]{4}$")
    fir: str | None = Field(default=None, pattern=r"^[A-Z]{4}$", description="Flight Information Region")
    category: NotamCategory = NotamCategory.NEW
    severity: NotamSeverity = NotamSeverity.NORMAL

    # Q-line (ICAO structured Q-code)
    q_fir: str | None = Field(default=None, pattern=r"^[A-Z]{4}$")
    q_code: str | None = Field(default=None, description="5-letter Q-code, e.g. 'QMRLC'")
    q_traffic: NotamTraffic | None = None
    q_purpose: list[NotamPurpose] = Field(default_factory=list)
    q_scope: list[NotamScope] = Field(default_factory=list)
    q_lower_limit_ft: int | None = Field(default=None, description="Lower vertical limit (ft)")
    q_upper_limit_ft: int | None = Field(default=None, description="Upper vertical limit (ft)")
    q_coords_lat: float | None = Field(default=None, ge=-90.0, le=90.0)
    q_coords_lon: float | None = Field(default=None, ge=-180.0, le=180.0)
    q_radius_nm: int | None = Field(default=None, description="Radius in nautical miles")

    # Content fields (ICAO item A-G)
    a_location: str | None = Field(default=None, description="Location, usually ICAO identifier")
    b_valid_from: datetime
    c_valid_to: datetime | None = Field(default=None, description="NULL if PERMANENT")
    d_schedule: str | None = Field(default=None, description="e.g. 'DAILY 0600-1800'")
    e_condition: str = Field(description="Main NOTAM text (English)")
    e_condition_de: str | None = None
    f_lower_limit: str | None = Field(default=None, description="e.g. 'SFC', 'FL100'")
    g_upper_limit: str | None = Field(default=None, description="e.g. '999', 'UNL'")

    raw_text: str = Field(description="Full raw NOTAM text as received")
    source_airac_cycle: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")


class NotamCreate(NotamBase):
    pass


class Notam(NotamBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
