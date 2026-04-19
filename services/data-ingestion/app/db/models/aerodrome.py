"""Aerodrome — top-level entity keyed by ICAO code."""

from decimal import Decimal
from typing import TYPE_CHECKING

from shared.models.base import AiracCycleMixin, TimestampMixin
from shared.schemas.enums import AerodromeType
from sqlalchemy import CHAR, Enum, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

if TYPE_CHECKING:
    from .chart import Chart
    from .frequency import Frequency
    from .notam import Notam
    from .runway import Runway


class Aerodrome(Base, TimestampMixin, AiracCycleMixin):
    __tablename__ = "aerodromes"
    __table_args__ = (
        Index("ix_aerodromes_name", "name"),
        Index("ix_aerodromes_name_de", "name_de"),
        Index("ix_aerodromes_city", "city"),
        Index("ix_aerodromes_type", "type"),
    )

    icao: Mapped[str] = mapped_column(CHAR(4), primary_key=True)
    iata: Mapped[str | None] = mapped_column(CHAR(3), nullable=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_de: Mapped[str | None] = mapped_column(String(200), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city_de: Mapped[str | None] = mapped_column(String(120), nullable=True)
    region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    region_de: Mapped[str | None] = mapped_column(String(80), nullable=True)
    country: Mapped[str] = mapped_column(CHAR(2), nullable=False, default="DE")

    type: Mapped[AerodromeType] = mapped_column(
        Enum(
            AerodromeType,
            name="aerodrome_type",
            schema="ingest",
            values_callable=lambda e: [m.value for m in e],
            create_type=False,
        ),
        nullable=False,
        default=AerodromeType.OTHER,
    )

    operator: Mapped[str | None] = mapped_column(String(200), nullable=True)
    operator_de: Mapped[str | None] = mapped_column(String(200), nullable=True)

    latitude: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    longitude: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    elevation_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    magnetic_variation: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    ref_point_remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ref_point_remark_de: Mapped[str | None] = mapped_column(String(500), nullable=True)

    runways: Mapped[list["Runway"]] = relationship(
        back_populates="aerodrome", cascade="all, delete-orphan"
    )
    frequencies: Mapped[list["Frequency"]] = relationship(
        back_populates="aerodrome", cascade="all, delete-orphan"
    )
    charts: Mapped[list["Chart"]] = relationship(
        back_populates="aerodrome", cascade="all, delete-orphan"
    )
    notams: Mapped[list["Notam"]] = relationship(back_populates="aerodrome")
