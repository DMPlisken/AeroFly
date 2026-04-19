# AeroFly — Bug Registry

Known bug patterns and their fixes. Check this when debugging to see if the issue matches a known pattern.

## Format

Each entry:
```
### [BUG-NNN] Short description
- **Symptom**: What the user/developer sees
- **Root cause**: Why it happens
- **Fix**: What was changed
- **Affected files**: List of files
- **Commit/PR**: Reference
```

---

### [BUG-001] Alembic migration re-creates Postgres enum types on every column
- **Symptom**: `psycopg2.errors.DuplicateObject: type "<name>" already exists` during `alembic upgrade head` when multiple columns reference the same `sa.Enum`, even after pre-creating the enum.
- **Root cause**: SQLAlchemy 2.0's `sa.Enum(..., create_type=False)` is not fully honored when the Enum is attached to a column via `op.create_table(...)`. The `before_create` event on the Table triggers `_on_table_create` on the Enum, which re-issues `CREATE TYPE`.
- **Fix**: Create enums with raw SQL (`op.execute('CREATE TYPE schema.name AS ENUM(...)')`), and reference them in columns via `postgresql.ENUM(..., create_type=False)` (the PG-specific variant honors the flag reliably). Also set `values_callable=lambda e: [m.value for m in e]` on every model Enum so SQLAlchemy sends the lowercase `.value` rather than the uppercase `.name` to Postgres.
- **Affected files**: `services/data-ingestion/alembic/versions/20260419_0001_initial_ingest_schema.py`, `services/data-ingestion/app/db/models/*.py`
- **Commit/PR**: #4

### [BUG-002] Alembic version_table_schema fails when service schema doesn't exist yet
- **Symptom**: `psycopg2.errors.InvalidSchemaName: schema "ingest" does not exist` when running the very first `alembic upgrade` against a fresh database with `version_table_schema` set to a custom schema.
- **Root cause**: Alembic creates its `alembic_version` table in the configured `version_table_schema` before any migration's `upgrade()` runs. If the first migration is the one that creates that schema, it's too late.
- **Fix**: In each service's `alembic/env.py`, execute `CREATE SCHEMA IF NOT EXISTS "<schema>"` on the connection *before* calling `context.configure(...)`, and commit before Alembic begins its own transaction.
- **Affected files**: `services/data-ingestion/alembic/env.py`, `services/search/alembic/env.py`, `services/gateway/alembic/env.py`
- **Commit/PR**: #4
