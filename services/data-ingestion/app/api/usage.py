"""Read-only endpoints exposing LLM API usage / cost."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.db import get_session_factory
from app.db.models import ApiUsage
from app.core.config import settings

router = APIRouter(prefix="/usage", tags=["usage"])

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


@router.get("/summary", summary="Aggregate usage stats")
def usage_summary(db: Annotated[Session, Depends(get_db)]) -> dict:
    """Return overall + per-provider totals."""
    totals = db.execute(
        select(
            func.count(ApiUsage.id),
            func.coalesce(func.sum(ApiUsage.input_tokens), 0),
            func.coalesce(func.sum(ApiUsage.output_tokens), 0),
            func.coalesce(func.sum(ApiUsage.cached_input_tokens), 0),
            func.coalesce(func.sum(ApiUsage.total_cost_usd), 0),
            func.coalesce(func.avg(ApiUsage.latency_ms), 0),
            func.coalesce(func.sum(func.cast(ApiUsage.success == False, Integer)), 0),  # noqa: E712
        )
    ).one()

    per_provider = db.execute(
        select(
            ApiUsage.provider,
            func.count(ApiUsage.id),
            func.coalesce(func.sum(ApiUsage.input_tokens), 0),
            func.coalesce(func.sum(ApiUsage.output_tokens), 0),
            func.coalesce(func.sum(ApiUsage.cached_input_tokens), 0),
            func.coalesce(func.sum(ApiUsage.total_cost_usd), 0),
        )
        .group_by(ApiUsage.provider)
    ).all()

    per_purpose = db.execute(
        select(
            ApiUsage.purpose,
            func.count(ApiUsage.id),
            func.coalesce(func.sum(ApiUsage.total_cost_usd), 0),
        )
        .group_by(ApiUsage.purpose)
    ).all()

    return {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "total_calls": int(totals[0]),
        "total_input_tokens": int(totals[1]),
        "total_output_tokens": int(totals[2]),
        "total_cached_input_tokens": int(totals[3]),
        "total_cost_usd": _as_str(totals[4]),
        "avg_latency_ms": int(totals[5] or 0),
        "failed_calls": int(totals[6]),
        "per_provider": [
            {
                "provider": row[0],
                "calls": int(row[1]),
                "input_tokens": int(row[2]),
                "output_tokens": int(row[3]),
                "cached_input_tokens": int(row[4]),
                "total_cost_usd": _as_str(row[5]),
            }
            for row in per_provider
        ],
        "per_purpose": [
            {
                "purpose": row[0],
                "calls": int(row[1]),
                "total_cost_usd": _as_str(row[2]),
            }
            for row in per_purpose
        ],
    }


@router.get("/recent", summary="Recent API calls")
def usage_recent(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict]:
    rows = db.execute(
        select(ApiUsage).order_by(ApiUsage.created_at.desc()).limit(limit)
    ).scalars().all()
    return [
        {
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "provider": r.provider,
            "model": r.model,
            "purpose": r.purpose,
            "aerodrome_icao": r.aerodrome_icao,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "cached_input_tokens": r.cached_input_tokens,
            "input_cost_usd": _as_str(r.input_cost_usd),
            "output_cost_usd": _as_str(r.output_cost_usd),
            "cached_input_cost_usd": _as_str(r.cached_input_cost_usd),
            "total_cost_usd": _as_str(r.total_cost_usd),
            "latency_ms": r.latency_ms,
            "success": r.success,
            "error_code": r.error_code,
        }
        for r in rows
    ]


def _as_str(value) -> str:
    """Serialize Decimal as string to preserve precision across JSON."""
    if value is None:
        return "0"
    return str(Decimal(value).quantize(Decimal("0.000001")))
