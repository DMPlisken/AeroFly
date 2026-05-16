"""SQLAlchemy engine, session factory, and FastAPI dependency for the gateway.

The gateway service owns the `gateway` Postgres schema. Most endpoints proxy
to data-ingestion, but a few (currently: favorites) require local persistence.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

GATEWAY_SCHEMA = "gateway"


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


class Base(DeclarativeBase):
    """Common declarative base for all gateway-owned ORM models."""


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
