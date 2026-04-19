"""Physical / legal constraint validator for aerodrome fields.

Safety-critical. A value that fails any constraint is REJECTED and never
reaches consensus — it is as if the source had returned null. This is the
innermost fail-closed guard: even if three providers agree on an impossible
value (e.g. a VHF frequency outside 108–137 MHz, a runway of 40 km), we
refuse to persist it.

All checks are pure functions on already-unit-normalized values (metres,
feet, MHz, decimal degrees). See `unit_normalizer.py` for the conversion
step that must run before these.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

# --- Ranges (German airspace + civil aviation norms) --------------------- #

# Runway physical characteristics (ICAO Annex 14 + German practice).
MIN_RUNWAY_LENGTH_M = 200
MAX_RUNWAY_LENGTH_M = 6_000
MIN_RUNWAY_WIDTH_M = 7
MAX_RUNWAY_WIDTH_M = 80

# Elevation for German aerodromes (Zugspitze heliport ≈ 9 700 ft is the cap).
MIN_ELEVATION_FT = -200
MAX_ELEVATION_FT = 15_000

# Magnetic variation for Central Europe (IGRF model).
MIN_MAG_VAR_DEG = Decimal("-15.0")
MAX_MAG_VAR_DEG = Decimal("15.0")

# Civil aeronautical VHF band.
MIN_FREQUENCY_MHZ = Decimal("108.000")
MAX_FREQUENCY_MHZ = Decimal("137.000")

# Coordinates — bounding box for Germany + safety margin.
MIN_LATITUDE = Decimal("47.0")
MAX_LATITUDE = Decimal("55.5")
MIN_LONGITUDE = Decimal("5.5")
MAX_LONGITUDE = Decimal("15.5")

# Tolerance when comparing runway designator to true heading.
RUNWAY_HEADING_TOLERANCE_DEG = Decimal("10.0")


class ValidationError(ValueError):
    """Raised when a value fails a domain constraint."""


def _coerce_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        return Decimal(value)
    raise ValidationError(f"not a numeric value: {value!r}")


def validate_runway_length_m(value: Any) -> int:
    v = int(_coerce_decimal(value))
    if not MIN_RUNWAY_LENGTH_M <= v <= MAX_RUNWAY_LENGTH_M:
        raise ValidationError(
            f"runway length {v} m out of plausible range "
            f"[{MIN_RUNWAY_LENGTH_M}, {MAX_RUNWAY_LENGTH_M}]"
        )
    return v


def validate_runway_width_m(value: Any) -> int:
    v = int(_coerce_decimal(value))
    if not MIN_RUNWAY_WIDTH_M <= v <= MAX_RUNWAY_WIDTH_M:
        raise ValidationError(
            f"runway width {v} m out of plausible range "
            f"[{MIN_RUNWAY_WIDTH_M}, {MAX_RUNWAY_WIDTH_M}]"
        )
    return v


def validate_elevation_ft(value: Any) -> int:
    v = int(_coerce_decimal(value))
    if not MIN_ELEVATION_FT <= v <= MAX_ELEVATION_FT:
        raise ValidationError(
            f"elevation {v} ft out of plausible range for Germany "
            f"[{MIN_ELEVATION_FT}, {MAX_ELEVATION_FT}]"
        )
    return v


def validate_mag_variation(value: Any) -> Decimal:
    v = _coerce_decimal(value)
    if not MIN_MAG_VAR_DEG <= v <= MAX_MAG_VAR_DEG:
        raise ValidationError(
            f"magnetic variation {v}° out of plausible range for Central Europe "
            f"[{MIN_MAG_VAR_DEG}, {MAX_MAG_VAR_DEG}]"
        )
    return v


def validate_frequency_mhz(value: Any) -> Decimal:
    v = _coerce_decimal(value)
    if not MIN_FREQUENCY_MHZ <= v <= MAX_FREQUENCY_MHZ:
        raise ValidationError(
            f"frequency {v} MHz outside civil aeronautical VHF band "
            f"[{MIN_FREQUENCY_MHZ}, {MAX_FREQUENCY_MHZ}]"
        )
    # 25 kHz or 8.33 kHz channel spacing is expected; reject weird fractions.
    step_25 = (v * 1000) % Decimal("25")
    step_833 = (v * 1000 * 3) % Decimal("25")  # 8.333… kHz = 1/3 of 25 kHz
    if step_25 != 0 and step_833 != 0:
        raise ValidationError(
            f"frequency {v} MHz not on 25 kHz or 8.33 kHz channel grid"
        )
    return v


def validate_latitude(value: Any) -> float:
    v = _coerce_decimal(value)
    if not MIN_LATITUDE <= v <= MAX_LATITUDE:
        raise ValidationError(
            f"latitude {v}° outside Germany bounding box [{MIN_LATITUDE}, {MAX_LATITUDE}]"
        )
    return float(v)


def validate_longitude(value: Any) -> float:
    v = _coerce_decimal(value)
    if not MIN_LONGITUDE <= v <= MAX_LONGITUDE:
        raise ValidationError(
            f"longitude {v}° outside Germany bounding box [{MIN_LONGITUDE}, {MAX_LONGITUDE}]"
        )
    return float(v)


def validate_runway_designator(designator: str) -> str:
    """RWY designator format: two digits (01-36) + optional L/C/R."""
    d = designator.strip().upper()
    if len(d) < 2 or len(d) > 3:
        raise ValidationError(f"runway designator {designator!r} must be 2 or 3 chars")
    num_part = d[:2]
    suffix = d[2:] if len(d) == 3 else ""
    if not num_part.isdigit():
        raise ValidationError(f"runway designator {designator!r} first two chars must be digits")
    num = int(num_part)
    if not 1 <= num <= 36:
        raise ValidationError(f"runway designator number {num} out of 01-36 range")
    if suffix and suffix not in ("L", "C", "R"):
        raise ValidationError(f"runway designator suffix {suffix!r} must be L / C / R")
    return d


def validate_runway_heading_vs_designator(
    designator: str, true_heading_deg: Any
) -> None:
    """Cross-check: runway true heading must match 10 × designator ± 10°.

    The classic aviation tripwire — catches wrong-RWY-labelled rows.
    """
    d = validate_runway_designator(designator)
    implied = int(d[:2]) * 10
    heading = _coerce_decimal(true_heading_deg) % 360
    # Compute minimum angular distance modulo 360.
    diff = min(abs(heading - implied), 360 - abs(heading - implied))
    if diff > RUNWAY_HEADING_TOLERANCE_DEG:
        raise ValidationError(
            f"runway {designator}: implied heading ~{implied}°, reported {heading}°, "
            f"diff {diff}° exceeds {RUNWAY_HEADING_TOLERANCE_DEG}° tolerance"
        )


def validate_icao(icao: str) -> str:
    v = icao.strip().upper()
    if len(v) != 4 or not v.isalpha():
        raise ValidationError(f"ICAO code {icao!r} must be 4 letters")
    return v


def validate_airac_cycle(cycle: str) -> str:
    """YYYY-MM format, year ≥ 2020, month 01-12."""
    v = cycle.strip()
    if len(v) != 7 or v[4] != "-":
        raise ValidationError(f"AIRAC cycle {cycle!r} must be 'YYYY-MM'")
    year_part, month_part = v.split("-")
    if not (year_part.isdigit() and month_part.isdigit()):
        raise ValidationError(f"AIRAC cycle {cycle!r} non-numeric")
    year = int(year_part)
    month = int(month_part)
    if not (2020 <= year <= 2100 and 1 <= month <= 12):
        raise ValidationError(f"AIRAC cycle {cycle!r} out of plausible range")
    return v
