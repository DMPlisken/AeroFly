"""Frequency — radio comms channel assigned to an aerodrome service."""

from decimal import Decimal
from typing import TYPE_CHECKING

from shared.models.base import AiracCycleMixin, TimestampMixin
from shared.schemas.enums import FrequencyType
from sqlalchemy import BigInteger, CHAR, Enum, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

if TYPE_CHECKING:
    from .aerodrome import Aerodrome


class Frequency(Base, TimestampMixin, AiracCycleMixin):
    __tablename__ = "frequencies"
    __table_args__ = (
        Index("ix_frequencies_aerodrome_icao", "aerodrome_icao"),
        Index("ix_frequencies_aerodrome_type", "aerodrome_icao", "type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    aerodrome_icao: Mapped[str] = mapped_column(
        CHAR(4), ForeignKey("aerodromes.icao", ondelete="CASCADE"), nullable=False
    )

    type: Mapped[FrequencyType] = mapped_column(
        Enum(
            FrequencyType,
            name="frequency_type",
            schema="ingest",
            values_callable=lambda e: [m.value for m in e],
            create_type=False,
        ),
        nullable=False,
    )
    callsign: Mapped[str | None] = mapped_column(String(120), nullable=True)
    callsign_de: Mapped[str | None] = mapped_column(String(120), nullable=True)
    frequency_mhz: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)

    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remark_de: Mapped[str | None] = mapped_column(String(500), nullable=True)
    operational_hours: Mapped[str | None] = mapped_column(String(240), nullable=True)
    operational_hours_de: Mapped[str | None] = mapped_column(String(240), nullable=True)

    aerodrome: Mapped["Aerodrome"] = relationship(back_populates="frequencies")
