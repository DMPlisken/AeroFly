"""Chart — PDF/image document scraped from DFS AIP for an aerodrome."""

from typing import TYPE_CHECKING

from shared.models.base import AiracCycleMixin, TimestampMixin
from shared.schemas.enums import ChartType
from sqlalchemy import BigInteger, CHAR, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

if TYPE_CHECKING:
    from .aerodrome import Aerodrome


class Chart(Base, TimestampMixin, AiracCycleMixin):
    __tablename__ = "charts"
    __table_args__ = (
        Index("ix_charts_aerodrome_icao", "aerodrome_icao"),
        Index("ix_charts_chart_type", "chart_type"),
        Index("ix_charts_source_url", "source_url", unique=True),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    aerodrome_icao: Mapped[str] = mapped_column(
        CHAR(4), ForeignKey("aerodromes.icao", ondelete="CASCADE"), nullable=False
    )

    chart_type: Mapped[ChartType] = mapped_column(
        Enum(
            ChartType,
            name="chart_type",
            schema="ingest",
            values_callable=lambda e: [m.value for m in e],
            create_type=False,
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    title_de: Mapped[str | None] = mapped_column(String(300), nullable=True)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    local_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    language: Mapped[str] = mapped_column(CHAR(2), nullable=False, default="de")

    aerodrome: Mapped["Aerodrome"] = relationship(back_populates="charts")
