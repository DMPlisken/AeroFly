"""Favorite — anonymous (device-id keyed) aerodrome bookmark."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import GATEWAY_SCHEMA, Base


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = {"schema": GATEWAY_SCHEMA}

    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    icao: Mapped[str] = mapped_column(String(8), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
