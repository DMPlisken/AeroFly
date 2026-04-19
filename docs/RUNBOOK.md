# AeroFly — Local Runbook

How to run the stack locally in under five minutes.

## Prerequisites

- Docker Desktop (or Docker Engine + compose v2)
- `bash` shell (WSL / Git Bash on Windows)
- ~2 GB free RAM

## First-time setup

```bash
# 1. Create local env file (gitignored).
cp .env.example .env

# 2. (Optional) Edit .env to adjust host-side ports if your machine already
#    runs Postgres/Redis/Meilisearch. Defaults avoid the common ports:
#      POSTGRES_PORT_HOST=55432
#      REDIS_PORT_HOST=56379
#      MEILI_PORT_HOST=57700
#      NGINX_PORT_HOST=8080
```

## Start the stack

```bash
docker compose up --build -d
```

Wait ~30 s for all services to become healthy:

```bash
docker compose ps
```

You should see `(healthy)` next to `postgres`, `redis`, `meilisearch`,
`gateway`, `data-ingestion`, and `search`. `frontend` and `nginx` do not
ship a healthcheck yet; they are either `running` or `exited`.

## Apply database migrations

```bash
bash scripts/migrate-all.sh
```

This runs `alembic upgrade head` inside each migration-owning container
(`data-ingestion`, `search`, `gateway`) and creates:

- `ingest.*` — 6 tables + 9 enums (authoritative domain data)
- `search.*` — empty (projections land when Meilisearch sync track starts)
- `gateway.*` — empty (API tables land when Gateway API track starts)

## Verify

| URL | What you should see |
|---|---|
| `http://localhost:8080/` | Frontend "Hello AeroFly" page (via nginx) |
| `http://localhost:8080/api/health` | `{"status":"ok","service":"gateway"}` |
| `http://localhost:8080/api/docs` | Swagger UI for the gateway |
| `http://localhost:18000/api/health` | Gateway directly |
| `http://localhost:18001/health` | Data-ingestion directly |
| `http://localhost:18001/docs` | Data-ingestion Swagger |
| `http://localhost:18002/health` | Search directly |
| `http://localhost:13000/` | Frontend Vite dev server directly |
| `http://localhost:17700/health` | Meilisearch |

## Smoke-test the database round-trip

With the stack running and migrations applied:

```bash
docker compose exec data-ingestion python scripts/smoke_test_db.py
```

Expected output (all OK lines):

```
OK  aerodrome          : ZZZZ / Smoketest Airport / Smoketest Flughafen
OK  runways            : 1
OK  frequencies        : 3
OK  charts             : 1
OK  notams             : 1
OK  airac cycle        : 2026-04
OK  rollback           : clean — no data persisted
```

## Shutdown

```bash
# Stop containers (keep volumes — next startup reuses DB)
docker compose stop

# Stop and remove containers (keep volumes)
docker compose down

# Stop, remove containers AND wipe volumes (clean slate)
docker compose down -v
```

## Troubleshooting

### `bind: address already in use`
Something on the host already listens on one of the default host ports.
Override it in `.env`:

```
POSTGRES_PORT_HOST=56789
REDIS_PORT_HOST=56780
MEILI_PORT_HOST=57701
NGINX_PORT_HOST=8081
```

### `env file .env not found`
You skipped the first-time setup. Run `cp .env.example .env`.

### Gateway / data-ingestion / search stuck in `starting`
Check logs: `docker compose logs -f <service>`. The most common cause is
that migrations haven't run yet and the healthcheck is timing out — but
the `/health` endpoint doesn't touch the DB, so this is unusual. If it
persists, restart: `docker compose restart <service>`.

### `schema "ingest" does not exist` when running smoke test
Run `bash scripts/migrate-all.sh` first.

### Fresh rebuild after a Dockerfile / requirements change
```bash
docker compose up --build -d --force-recreate
```

## Ports reference (defaults)

| Service | Inside container | Host default | Override var |
|---|---|---|---|
| postgres | 5432 | 15432 | `POSTGRES_PORT_HOST` |
| redis | 6379 | 16379 | `REDIS_PORT_HOST` |
| meilisearch | 7700 | 17700 | `MEILI_PORT_HOST` |
| gateway | 8000 | 18000 | `GATEWAY_PORT_HOST` |
| data-ingestion | 8001 | 18001 | `DATA_INGESTION_PORT_HOST` |
| search | 8002 | 18002 | `SEARCH_PORT_HOST` |
| frontend | 3000 | 13000 | `FRONTEND_PORT_HOST` |
| nginx | 80 | 8080 | `NGINX_PORT_HOST` |

Defaults are offset into high ranges because the common `8000/8001/8002/3000`
ports are frequently in use by other local projects.
