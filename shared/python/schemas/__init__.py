"""Shared Pydantic schemas — the cross-service contract for AeroFly domain data.

These models are the single source of truth for payloads exchanged between
services (HTTP request/response bodies, Redis pub/sub event bodies) and for
validating ingested data before persistence.

Each service defines its own SQLAlchemy models against its own PostgreSQL
schema; the Pydantic types here describe the domain independently of storage.
"""

from .aerodrome import Aerodrome, AerodromeBase, AerodromeCreate, AerodromeUpdate
from .airac_cycle import AiracCycle, AiracCycleBase, AiracCycleCreate
from .chart import Chart, ChartBase, ChartCreate
from .enums import (
    AerodromeType,
    ChartType,
    FrequencyType,
    NotamCategory,
    NotamPurpose,
    NotamScope,
    NotamSeverity,
    NotamTraffic,
    RunwaySurface,
)
from .frequency import Frequency, FrequencyBase, FrequencyCreate
from .notam import Notam, NotamBase, NotamCreate
from .runway import Runway, RunwayBase, RunwayCreate

__all__ = [
    "AerodromeType",
    "ChartType",
    "FrequencyType",
    "NotamCategory",
    "NotamPurpose",
    "NotamScope",
    "NotamSeverity",
    "NotamTraffic",
    "RunwaySurface",
    "Aerodrome",
    "AerodromeBase",
    "AerodromeCreate",
    "AerodromeUpdate",
    "AiracCycle",
    "AiracCycleBase",
    "AiracCycleCreate",
    "Chart",
    "ChartBase",
    "ChartCreate",
    "Frequency",
    "FrequencyBase",
    "FrequencyCreate",
    "Notam",
    "NotamBase",
    "NotamCreate",
    "Runway",
    "RunwayBase",
    "RunwayCreate",
]
