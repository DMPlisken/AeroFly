"""Database layer for the data-ingestion service.

Owns the authoritative `ingest` PostgreSQL schema: every aerodrome row
originates here. Other services subscribe to change events and maintain
their own projections.
"""

from .base import Base, SCHEMA_NAME, get_engine, get_session_factory

__all__ = ["Base", "SCHEMA_NAME", "get_engine", "get_session_factory"]
