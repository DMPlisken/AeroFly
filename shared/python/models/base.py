"""Shared SQLAlchemy base and cross-cutting mixins.

Each service subclasses `Base` or binds its own `MetaData` so schemas remain
isolated per service (see CLAUDE.md: database per module). Mixins capture the
columns every AeroFly domain row must carry regardless of which service owns
the schema.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Default declarative base. Services may subclass or supply their own MetaData."""


class TimestampMixin:
    """Adds created_at / updated_at columns driven by the database server."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AiracCycleMixin:
    """Records which AIRAC cycle supplied the current value of a row.

    Re-ingesting a cycle and comparing `source_airac_cycle` lets us detect
    deltas without storing a full history.
    """

    source_airac_cycle: Mapped[str | None] = mapped_column(String(7), nullable=True, index=True)
