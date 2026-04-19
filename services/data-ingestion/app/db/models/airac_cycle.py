"""AIRAC cycle metadata — 28-day aeronautical info regulation period."""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base


class AiracCycle(Base):
    __tablename__ = "airac_cycles"

    ident: Mapped[str] = mapped_column(String(7), primary_key=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
