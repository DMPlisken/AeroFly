"""NOTAM — Notice to Airmen, structured per ICAO Annex 15 Appendix 6."""

from datetime import datetime
from typing import TYPE_CHECKING

from shared.models.base import AiracCycleMixin, TimestampMixin
from shared.schemas.enums import (
    NotamCategory,
    NotamPurpose,
    NotamScope,
    NotamSeverity,
    NotamTraffic,
)
from sqlalchemy import (
    ARRAY,
    BigInteger,
    CHAR,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import Base

if TYPE_CHECKING:
    from .aerodrome import Aerodrome


class Notam(Base, TimestampMixin, AiracCycleMixin):
    __tablename__ = "notams"
    __table_args__ = (
        Index("ix_notams_notam_id", "notam_id", unique=True),
        Index("ix_notams_aerodrome_icao", "aerodrome_icao"),
        Index("ix_notams_valid_from", "b_valid_from"),
        Index("ix_notams_severity", "severity"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    notam_id: Mapped[str] = mapped_column(String(32), nullable=False)
    aerodrome_icao: Mapped[str | None] = mapped_column(
        CHAR(4), ForeignKey("aerodromes.icao", ondelete="SET NULL"), nullable=True
    )
    fir: Mapped[str | None] = mapped_column(CHAR(4), nullable=True)

    category: Mapped[NotamCategory] = mapped_column(
        Enum(
            NotamCategory,
            name="notam_category",
            schema="ingest",
            values_callable=lambda e: [m.value for m in e],
            create_type=False,
        ),
        nullable=False,
        default=NotamCategory.NEW,
    )
    severity: Mapped[NotamSeverity] = mapped_column(
        Enum(
            NotamSeverity,
            name="notam_severity",
            schema="ingest",
            values_callable=lambda e: [m.value for m in e],
            create_type=False,
        ),
        nullable=False,
        default=NotamSeverity.NORMAL,
    )

    # Q-line (ICAO structured)
    q_fir: Mapped[str | None] = mapped_column(CHAR(4), nullable=True)
    q_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    q_traffic: Mapped[NotamTraffic | None] = mapped_column(
        Enum(
            NotamTraffic,
            name="notam_traffic",
            schema="ingest",
            values_callable=lambda e: [m.value for m in e],
            create_type=False,
        ),
        nullable=True,
    )
    q_purpose: Mapped[list[NotamPurpose]] = mapped_column(
        ARRAY(
            Enum(
                NotamPurpose,
                name="notam_purpose",
                schema="ingest",
                values_callable=lambda e: [m.value for m in e],
                create_type=False,
            )
        ),
        nullable=False,
        default=list,
    )
    q_scope: Mapped[list[NotamScope]] = mapped_column(
        ARRAY(
            Enum(
                NotamScope,
                name="notam_scope",
                schema="ingest",
                values_callable=lambda e: [m.value for m in e],
                create_type=False,
            )
        ),
        nullable=False,
        default=list,
    )
    q_lower_limit_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    q_upper_limit_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    q_coords_lat: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    q_coords_lon: Mapped[float | None] = mapped_column(DOUBLE_PRECISION, nullable=True)
    q_radius_nm: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Content fields (ICAO item A-G)
    a_location: Mapped[str | None] = mapped_column(CHAR(4), nullable=True)
    b_valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    c_valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    d_schedule: Mapped[str | None] = mapped_column(String(500), nullable=True)
    e_condition: Mapped[str] = mapped_column(Text, nullable=False)
    e_condition_de: Mapped[str | None] = mapped_column(Text, nullable=True)
    f_lower_limit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    g_upper_limit: Mapped[str | None] = mapped_column(String(40), nullable=True)

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)

    aerodrome: Mapped["Aerodrome | None"] = relationship(back_populates="notams")
