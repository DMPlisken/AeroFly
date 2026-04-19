"""Runway — physical runway with low-end (LE) and high-end (HE) designators."""

from decimal import Decimal
from typing import TYPE_CHECKING

from shared.models.base import AiracCycleMixin, TimestampMixin
from shared.schemas.enums import RunwaySurface
from sqlalchemy import (
    BigInteger,
    Boolean,
    CHAR,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

if TYPE_CHECKING:
    from .aerodrome import Aerodrome


class Runway(Base, TimestampMixin, AiracCycleMixin):
    __tablename__ = "runways"
    __table_args__ = (
        UniqueConstraint(
            "aerodrome_icao", "designator_le", "designator_he", name="uq_runway_designator"
        ),
        Index("ix_runways_aerodrome_icao", "aerodrome_icao"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    aerodrome_icao: Mapped[str] = mapped_column(
        CHAR(4), ForeignKey("aerodromes.icao", ondelete="CASCADE"), nullable=False
    )

    designator_le: Mapped[str] = mapped_column(String(4), nullable=False)
    designator_he: Mapped[str] = mapped_column(String(4), nullable=False)
    true_heading_le: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    true_heading_he: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    length_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    surface: Mapped[RunwaySurface] = mapped_column(
        Enum(
            RunwaySurface,
            name="runway_surface",
            schema="ingest",
            values_callable=lambda e: [m.value for m in e],
            create_type=False,
        ),
        nullable=False,
        default=RunwaySurface.OTHER,
    )
    strength: Mapped[str | None] = mapped_column(String(120), nullable=True)

    le_thr_elevation_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    he_thr_elevation_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)

    le_tora_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    le_toda_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    le_asda_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    le_lda_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    he_tora_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    he_toda_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    he_asda_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    he_lda_m: Mapped[int | None] = mapped_column(Integer, nullable=True)

    ils_le: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ils_he: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    remark: Mapped[str | None] = mapped_column(String(500), nullable=True)
    remark_de: Mapped[str | None] = mapped_column(String(500), nullable=True)

    aerodrome: Mapped["Aerodrome"] = relationship(back_populates="runways")
