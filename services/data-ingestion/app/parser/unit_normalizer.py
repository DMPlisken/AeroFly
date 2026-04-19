"""Unit normalization before consensus comparison.

Two providers can extract the "same" value in different units or formats.
We normalize to a single canonical form per field-type so that
`normalize("13123 ft", field="length_m") == normalize("4000", field="length_m")`.

Every extracted value MUST pass through this module before the consensus
engine compares it. This catches the Mars-Climate-Orbiter-style unit
confusion that a generic string-equality check would miss.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

M_PER_FT = Decimal("0.3048")
FT_PER_M = Decimal("3.28084")
NM_PER_KM = Decimal("0.539957")


class UnitError(ValueError):
    """Raised when a unit cannot be recognised or converted."""


_NUMBER_RE = re.compile(
    r"""
    (?P<num>[-+]?[\d\.,\s]+)
    \s*
    (?P<unit>[A-Za-z°'"]+)?
    """,
    re.VERBOSE,
)


def _parse_decimal(text: str) -> Decimal:
    # Allow German decimal comma, strip thousands separators.
    cleaned = text.strip().replace(" ", "").replace("\u00a0", "")
    # If there's both "." and "," the comma is decimal, dots are thousands-sep.
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    return Decimal(cleaned)


def normalize_length_to_m(value: Any) -> int:
    """Accept '4000 m', '4000', '13123 ft', '13,123 ft' → round to int metres."""
    if isinstance(value, (int, float, Decimal)):
        # Bare number is assumed to be metres (documented contract).
        return int(Decimal(str(value)).to_integral_value(rounding=ROUND_HALF_UP))

    text = str(value).strip()
    match = _NUMBER_RE.fullmatch(text)
    if not match:
        raise UnitError(f"cannot parse length: {value!r}")

    num = _parse_decimal(match["num"])
    unit = (match["unit"] or "M").upper().replace("METERS", "M").replace("METRES", "M")
    if unit in {"M", "METER", "METRE"}:
        result = num
    elif unit in {"FT", "FEET", "'"}:
        result = num * M_PER_FT
    elif unit in {"KM"}:
        result = num * 1000
    else:
        raise UnitError(f"unknown length unit {unit!r} in {value!r}")

    return int(result.to_integral_value(rounding=ROUND_HALF_UP))


def normalize_elevation_to_ft(value: Any) -> int:
    """Accept '1487 ft', '1487', '453 m', '453,2 m' → round to int feet."""
    if isinstance(value, (int, float, Decimal)):
        return int(Decimal(str(value)).to_integral_value(rounding=ROUND_HALF_UP))

    text = str(value).strip()
    match = _NUMBER_RE.fullmatch(text)
    if not match:
        raise UnitError(f"cannot parse elevation: {value!r}")

    num = _parse_decimal(match["num"])
    unit = (match["unit"] or "FT").upper()
    if unit in {"FT", "FEET", "'"}:
        result = num
    elif unit in {"M", "METER", "METRE"}:
        result = num * FT_PER_M
    else:
        raise UnitError(f"unknown elevation unit {unit!r} in {value!r}")

    return int(result.to_integral_value(rounding=ROUND_HALF_UP))


def normalize_frequency_mhz(value: Any) -> Decimal:
    """Accept '118.700', '118,700', '118.7', 118700 (kHz?) → Decimal MHz @ 3 dp."""
    if isinstance(value, (int, float, Decimal)):
        v = Decimal(str(value))
    else:
        v = _parse_decimal(str(value))

    # Heuristic: if the value looks like kHz (big integer), convert.
    if v > 10_000:
        v = v / 1000  # kHz -> MHz

    return v.quantize(Decimal("0.001"))


def normalize_decimal_degree(value: Any) -> float:
    """Accept decimal '48.3538', DMS 'N48°21'13"' → float degrees."""
    if isinstance(value, (int, float, Decimal)):
        return float(Decimal(str(value)))

    text = str(value).strip().upper()

    # DMS pattern: optional hemisphere letter + deg + min + sec
    dms = re.match(
        r"""^\s*
        (?:(?P<hem>[NSEW])\s*)?
        (?P<deg>\d+(?:[\.,]\d+)?)\s*[°:]?\s*
        (?:(?P<min>\d+(?:[\.,]\d+)?)\s*['′:]?\s*)?
        (?:(?P<sec>\d+(?:[\.,]\d+)?)\s*["″]?\s*)?
        (?:(?P<hem2>[NSEW])\s*)?
        $""",
        text,
        re.VERBOSE,
    )
    if dms:
        deg = _parse_decimal(dms["deg"])
        minutes = _parse_decimal(dms["min"]) if dms["min"] else Decimal("0")
        seconds = _parse_decimal(dms["sec"]) if dms["sec"] else Decimal("0")
        value_dec = deg + minutes / 60 + seconds / 3600
        hemisphere = (dms["hem"] or dms["hem2"] or "").upper()
        if hemisphere in ("S", "W"):
            value_dec = -value_dec
        return float(value_dec)

    raise UnitError(f"cannot parse coordinate: {value!r}")


def normalize_text(value: Any) -> str:
    """Unicode NFC + strip + collapse whitespace; used for operator/city/region."""
    if value is None:
        return ""
    s = unicodedata.normalize("NFC", str(value)).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def normalize(field: str, value: Any) -> Any:
    """Dispatch by field name. Unknown fields pass through as normalized text."""
    if value is None:
        return None
    if field in {"length_m", "width_m"}:
        return normalize_length_to_m(value)
    if field == "elevation_ft":
        return normalize_elevation_to_ft(value)
    if field == "frequency_mhz":
        return normalize_frequency_mhz(value)
    if field in {"latitude", "longitude", "true_heading"}:
        return normalize_decimal_degree(value)
    return normalize_text(value)
