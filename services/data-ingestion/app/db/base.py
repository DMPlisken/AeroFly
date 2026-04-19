"""SQLAlchemy Base and session factory for the data-ingestion service.

All ORM models live in the `ingest` PostgreSQL schema. The schema is created
by the initial Alembic migration.
"""

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SCHEMA_NAME = "ingest"

_metadata = MetaData(schema=SCHEMA_NAME)


class Base(DeclarativeBase):
    metadata = _metadata


def get_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True, future=True)


def get_session_factory(database_url: str):
    return sessionmaker(
        bind=get_engine(database_url),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
