"""Shared pytest fixtures for the gateway service.

Uses the Postgres instance that CI / `docker compose -f docker-compose.test.yml`
already provide. Connection settings are read from the standard `POSTGRES_*`
env vars (defaulted by `app.core.config.Settings`).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import GATEWAY_SCHEMA, Base, SessionLocal, engine
from app.main import app

# Import models so they register on Base.metadata before create_all().
from app.models import favorite as _favorite_model  # noqa: F401


def _postgres_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


_HAS_POSTGRES = _postgres_available()
_skip_if_no_db = pytest.mark.skipif(
    not _HAS_POSTGRES,
    reason="No reachable Postgres for gateway tests (start docker-compose.test.yml).",
)


@pytest.fixture(scope="session", autouse=True)
def _prepare_schema() -> Iterator[None]:
    """Create the gateway schema + tables once for the test session.

    We deliberately do NOT drop tables on teardown: the tests may share a DB
    with a running dev stack (dev workflow runs pytest against the same
    Postgres). Per-test `truncate` in `db_session` is enough for isolation;
    dropping would wipe state the dev stack depends on between runs.
    """
    if not _HAS_POSTGRES:
        yield
        return
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{GATEWAY_SCHEMA}"'))
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def db_session() -> Iterator[Session]:
    """Per-test session that truncates favorites before each test."""
    session = SessionLocal()
    try:
        session.execute(text(f'TRUNCATE TABLE "{GATEWAY_SCHEMA}"."favorites"'))
        session.commit()
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session) -> Iterator[TestClient]:
    """FastAPI TestClient. db_session fixture guarantees a clean table."""
    with TestClient(app) as test_client:
        yield test_client


def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    """Auto-skip DB-bound tests when Postgres is not reachable."""
    if _HAS_POSTGRES:
        return
    for item in items:
        if "client" in item.fixturenames or "db_session" in item.fixturenames:
            item.add_marker(_skip_if_no_db)
