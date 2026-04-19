"""Read endpoints for the aerodrome domain.

Interim home — the Search service will take over read traffic once
Meilisearch + projection sync is wired up (tracked in OVERVIEW.md).
Until then, the owner of the authoritative schema also serves reads.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_session_factory
from app.db.models import Aerodrome
from app.core.config import settings
from shared.schemas import (
    Aerodrome as AerodromeSchema,
    AerodromeType,
)
from shared.schemas.aerodrome import AerodromeBase

router = APIRouter(prefix="/aerodromes", tags=["aerodromes"])

_SessionFactory = None


def _get_session_factory():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = get_session_factory(settings.database_url)
    return _SessionFactory


def get_db():
    session = _get_session_factory()()
    try:
        yield session
    finally:
        session.close()


# --- Response models that compose relationships for the detail endpoint --- #

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class RunwayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    designator_le: str
    designator_he: str
    length_m: int | None
    width_m: int | None
    surface: str
    ils_le: bool
    ils_he: bool


class FrequencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    callsign: str | None
    callsign_de: str | None
    frequency_mhz: Decimal


class ChartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    chart_type: str
    title: str
    title_de: str | None
    source_url: str


class NotamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    notam_id: str
    severity: str
    b_valid_from: datetime
    c_valid_to: datetime | None
    e_condition: str
    e_condition_de: str | None


class AerodromeDetail(AerodromeBase):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    updated_at: datetime
    runways: list[RunwayRead] = []
    frequencies: list[FrequencyRead] = []
    charts: list[ChartRead] = []
    notams: list[NotamRead] = []


# --- Endpoints --- #


@router.get("", response_model=list[AerodromeSchema])
def list_aerodromes(
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    q: str | None = Query(default=None, description="Prefix match against ICAO / name / name_de", max_length=120),
    type: AerodromeType | None = Query(default=None, description="Filter by aerodrome type"),
    region: str | None = Query(default=None, description="Filter by region (EN or DE)", max_length=80),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AerodromeSchema]:
    """List aerodromes with optional text, type and region filters.

    Sets the `X-Total-Count` response header with the pre-pagination total.
    """
    stmt = select(Aerodrome)
    count_stmt = select(func.count()).select_from(Aerodrome)

    if q:
        pattern = f"{q}%"
        ci_pattern = f"{q.upper()}%"
        clauses = or_(
            func.upper(Aerodrome.icao).like(ci_pattern),
            Aerodrome.name.ilike(pattern),
            Aerodrome.name_de.ilike(pattern),
        )
        stmt = stmt.where(clauses)
        count_stmt = count_stmt.where(clauses)
    if type is not None:
        stmt = stmt.where(Aerodrome.type == type)
        count_stmt = count_stmt.where(Aerodrome.type == type)
    if region:
        region_clause = or_(Aerodrome.region == region, Aerodrome.region_de == region)
        stmt = stmt.where(region_clause)
        count_stmt = count_stmt.where(region_clause)

    total = db.execute(count_stmt).scalar_one()
    response.headers["X-Total-Count"] = str(total)

    stmt = stmt.order_by(Aerodrome.icao).offset(offset).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [AerodromeSchema.model_validate(r) for r in rows]


@router.get("/{icao}", response_model=AerodromeDetail)
def get_aerodrome(
    icao: str,
    db: Annotated[Session, Depends(get_db)],
) -> AerodromeDetail:
    """Return one aerodrome with its runways, frequencies, charts, and NOTAMs."""
    icao_upper = icao.upper()
    if len(icao_upper) != 4 or not icao_upper.isalpha():
        raise HTTPException(status_code=400, detail="ICAO must be four letters")

    stmt = (
        select(Aerodrome)
        .where(Aerodrome.icao == icao_upper)
        .options(
            selectinload(Aerodrome.runways),
            selectinload(Aerodrome.frequencies),
            selectinload(Aerodrome.charts),
            selectinload(Aerodrome.notams),
        )
    )
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Aerodrome {icao_upper} not found")
    return AerodromeDetail.model_validate(row)
