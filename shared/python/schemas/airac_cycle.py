"""AIRAC cycle — 28-day aeronautical information regulation period."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class AiracCycleBase(BaseModel):
    ident: str = Field(pattern=r"^\d{4}-\d{2}$", description="Cycle identifier, e.g. '2026-04'")
    effective_from: date
    effective_to: date
    is_current: bool = False


class AiracCycleCreate(AiracCycleBase):
    pass


class AiracCycle(AiracCycleBase):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
