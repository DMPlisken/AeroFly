"""Shared SQLAlchemy building blocks — Base + mixins.

Services build their own declarative models on top of these; tables live in
per-service Postgres schemas (ingest / search / gateway) so nothing is shared
at the storage layer.
"""

from .base import AiracCycleMixin, Base, TimestampMixin

__all__ = ["AiracCycleMixin", "Base", "TimestampMixin"]
