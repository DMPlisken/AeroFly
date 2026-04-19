"""Shared domain enumerations.

Authoritative vocabulary for aerodrome data. Used by:
- Pydantic schemas (wire contract between services)
- Each service's SQLAlchemy models (as the source for Postgres enum types)
- Redis pub/sub event payloads
"""

from enum import Enum


class AerodromeType(str, Enum):
    INTERNATIONAL = "international"
    REGIONAL = "regional"
    GENERAL_AVIATION = "general_aviation"
    MILITARY = "military"
    PRIVATE = "private"
    OTHER = "other"


class RunwaySurface(str, Enum):
    ASPHALT = "asphalt"
    CONCRETE = "concrete"
    GRASS = "grass"
    GRAVEL = "gravel"
    SAND = "sand"
    WATER = "water"
    SNOW = "snow"
    OTHER = "other"


class FrequencyType(str, Enum):
    TWR = "twr"
    GND = "gnd"
    ATIS = "atis"
    AFIS = "afis"
    APP = "app"
    DEP = "dep"
    DEL = "del"
    INFO = "info"
    RADIO = "radio"
    CTA = "cta"
    FIS = "fis"
    EMERGENCY = "emergency"
    OTHER = "other"


class ChartType(str, Enum):
    AD_INFO = "ad_info"
    AD_CHART = "ad_chart"
    PARKING = "parking"
    TAXI = "taxi"
    SID = "sid"
    STAR = "star"
    IAC = "iac"
    VAC = "vac"
    GENERAL = "general"
    OTHER = "other"


class NotamCategory(str, Enum):
    NEW = "new"
    REPLACE = "replace"
    CANCEL = "cancel"


class NotamSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class NotamTraffic(str, Enum):
    IFR = "ifr"
    VFR = "vfr"
    IFR_VFR = "ifr_vfr"
    CHECKLIST = "checklist"


class NotamPurpose(str, Enum):
    """ICAO purpose flags — a NOTAM may have multiple (stored as array)."""
    NBO = "nbo"  # Immediate attention
    BO = "bo"    # Operational significance
    M = "m"      # Miscellaneous
    K = "k"      # Checklist


class NotamScope(str, Enum):
    """ICAO scope flags — a NOTAM may have multiple (stored as array)."""
    AERODROME = "aerodrome"
    EN_ROUTE = "en_route"
    NAV_WARNING = "nav_warning"
    CHECKLIST = "checklist"
