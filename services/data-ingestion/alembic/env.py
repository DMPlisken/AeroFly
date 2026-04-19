"""Alembic environment for the data-ingestion service.

Resolves `DATABASE_URL` from environment. Falls back to the docker-compose
default when unset so migrations can still be generated locally before a full
.env is configured. Adjusts sys.path so both in-container (`shared.schemas`)
and local-dev (`shared.python.schemas`) imports resolve.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool, text

_service_root = Path(__file__).resolve().parent.parent
_project_root = _service_root.parent.parent

# In-container: shared/python is mounted at /app/shared -> sibling import works.
# Local dev: add project root so `shared.python.*` is importable.
sys.path.insert(0, str(_service_root))
sys.path.insert(0, str(_project_root))
_shared_in_container = _service_root / "shared"
if _shared_in_container.exists():
    sys.path.insert(0, str(_shared_in_container.parent))

# Some contexts only have the repo layout available; alias `shared.python.*`
# -> `shared.*` so the service models (which import `shared.schemas.enums`)
# work both in-container and locally.
try:  # pragma: no cover - import plumbing
    import shared.schemas  # noqa: F401
except ModuleNotFoundError:
    import shared.python as _shared_pkg  # type: ignore
    import shared.python.models as _shared_models  # type: ignore
    import shared.python.models.base as _shared_models_base  # type: ignore
    import shared.python.schemas as _shared_schemas  # type: ignore
    import shared.python.schemas.enums as _shared_schemas_enums  # type: ignore

    sys.modules.setdefault("shared", _shared_pkg)
    sys.modules.setdefault("shared.schemas", _shared_schemas)
    sys.modules.setdefault("shared.schemas.enums", _shared_schemas_enums)
    sys.modules.setdefault("shared.models", _shared_models)
    sys.modules.setdefault("shared.models.base", _shared_models_base)

from app.db.base import SCHEMA_NAME, Base  # noqa: E402
from app.db import models  # noqa: E402,F401  ensures all tables are registered

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    user = os.getenv("POSTGRES_USER", "aerofly")
    password = os.getenv("POSTGRES_PASSWORD", "changeme")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "aerofly")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


config.set_main_option("sqlalchemy.url", _database_url())

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """Only manage objects that belong to our schema."""
    if type_ == "table" and obj.schema != SCHEMA_NAME:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema=SCHEMA_NAME,
        include_schemas=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        # Ensure the schema exists before alembic creates its version table in it.
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA_NAME}"'))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=SCHEMA_NAME,
            include_schemas=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
