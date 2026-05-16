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

### [BUG-003] nginx returns 502 for /api/* after rebuilding gateway/data-ingestion — **FIXED #51 / PR pending**
- **Symptom**: Frontend looks broken after `docker compose up --build -d` touches a backend service. Static assets load (React app renders), but every `/api/*` call returns 502. `docker compose ps` shows all services healthy.
- **Root cause**: nginx resolves upstream hostnames once at startup and caches the IPs. When a backend container is recreated, it gets a new internal IP on the compose network; nginx keeps trying the old IP and the kernel returns `connect() failed (111: Connection refused)` to nginx, which replies 502 to the client.
- **Workaround (pre-fix)**: `docker compose restart nginx` after any rebuild that recreated a backend container.
- **Permanent fix (issue #51)**: `infrastructure/nginx/nginx.conf` now uses Docker's embedded DNS (`resolver 127.0.0.11 valid=10s ipv6=off;`) plus variable-based `proxy_pass` (e.g. `set $upstream_gateway "gateway:8000"; proxy_pass http://$upstream_gateway$request_uri;`). Variable-form `proxy_pass` forces nginx to re-resolve the hostname at request time (cached for 10 s) rather than once at startup. Backends can now be rebuilt without a nginx restart — the new IP is picked up automatically within ~10 s.
- **Affected files**: `infrastructure/nginx/nginx.conf`.
- **Commit/PR**: discovered during #32 spike validation, recurred during #47 housekeeping, fixed via #51.

### [BUG-004] Manifest-driven chart_selector returns empty on pre-#30 manifests
- **Symptom**: After merging #32, running the extraction spike reports `"no chart matched the field group's accepted chart_types"` for every aerodrome — even though `data/aerodromes/<ICAO>/manifest.json` exists.
- **Root cause**: The selector filters on `chart_type` / `chart_suffix` fields added to the manifest schema by PR #30. Manifests already on disk were scraped before #30 and don't carry those fields, so the filter rejects every document.
- **Fix**: One-off backfill — iterate `data/aerodromes/*/manifest.json`, apply `classify_chart_type()` + `extract_chart_suffix()` to each document missing the fields, write back. Ran against 433 manifests / 1363 documents. Fresh scrapes already produce tagged manifests.
- **Affected files**: `data/aerodromes/*/manifest.json`.
- **Commit/PR**: discovered during #32 spike validation.

### [BUG-005] Chart viewer modal collapses + flickers after rotation
- **Symptom**: After clicking a rotation button in the chart viewer, the modal body shrinks to a thin horizontal strip (~200 px tall) and the viewer flickers open/closed rapidly, making the UI unusable.
- **Root cause**: Two compounding issues. (1) An inner `<div class="chart-viewer-rotation-host">` wrapper was added inside `react-zoom-pan-pinch`'s `TransformComponent`. RZPP measures its content's intrinsic size to compute fit; the percentage-sized wrapper had no intrinsic size of its own, so RZPP collapsed the stage to ~0 height. (2) A `ResizeObserver` was attached to that same wrapper to drive the rotated image's `max-width`/`max-height`. Updating those styles changed the wrapper's box, the observer fired again, and so on — a classic feedback loop.
- **Fix**: Remove the inner wrapper, render `<img>` directly inside `TransformComponent` (pre-rotation layout). Replace `ResizeObserver` with a one-shot `useLayoutEffect` keyed on `rotation` plus a `window` resize listener; re-measure only when the user actually rotates or resizes the viewport.
- **Affected files**: `services/frontend/src/components/ChartViewer.tsx`, `services/frontend/src/styles/global.css`
- **Commit/PR**: #44 (caught during initial UI test on EDDK Koeln Bonn 3 — fixed before merge).

### [BUG-006] Multi-document print forces all pages into one orientation
- **Symptom**: Printing multiple charts at once (Alle drucken / Auswahl drucken) at an aerodrome with mixed page orientations (e.g. EDDV: AD 2-4-3 + EDDV Hannover 2 are portrait, others are landscape) prints the minority pages in the wrong orientation. Single-print works correctly.
- **Root cause**: `printDocuments()` injected one global `@page { size: A4 ${orientation} }` rule chosen by majority vote across all measured charts. CSS `@page` is per-print-job, not per-page, when there is only one anonymous rule — so every page in the job inherits the majority orientation.
- **Fix**: Define **two named page rules** in the print stylesheet — `@page portrait { size: A4 portrait }` and `@page landscape { size: A4 landscape }` — and bind each `.print-page` element to the matching one via `page: portrait | landscape`. The helper now tags each generated page with `print-page--portrait` or `print-page--landscape` based on its own measured aspect ratio (after rotation) and removes the dynamic `<style>` injection entirely.
- **Affected files**: `services/frontend/src/styles/global.css`, `services/frontend/src/utils/printDocuments.ts`
- **Commit/PR**: #47 (caught during EDDV multi-print verification — fixed before merge).

### [BUG-007] Print pages overflow into 2-3 sheets per chart, rotated charts shifted off-center
- **Symptom**: After fixing per-page orientation (BUG-006), every printed chart spanned 2-3 A4 sheets (often blank first page, then image continuing onto the next). Charts with stored rotation appeared off-center and pushed to the right, causing further overflow.
- **Root cause**: Two compounding layout problems. (1) `.print-page` was sized with `height: 100vh`. In print contexts, browsers commit screen-viewport heights into the print layout BEFORE re-laying-out for the actual page size — `vh` is unreliable for print-size containers. The screen viewport (often >800px) was consistently larger than a 277mm A4 page, so the fixed-height `.print-page` flexbox overflowed onto extra sheets. (2) Rotated images (`transform: rotate(90deg)` etc.) keep their pre-rotation **layout box**; the visual rotates around the box's center but the layout footprint stays the same. With `flex` centering, the layout box stayed where it was, but the visual rotated outward — visually shifting right and overflowing the wrap horizontally.
- **Fix**: (a) Replace `height: 100vh` with explicit `mm` dimensions matching the printable area: `.print-page--portrait { width: 190mm; height: 277mm }`, `.print-page--landscape { width: 277mm; height: 190mm }` (= A4 paper minus the `@page { margin: 10mm }`). Add `box-sizing: border-box`, `overflow: hidden`, and `page-break-inside: avoid` for defense in depth. Reset `html, body { margin: 0; padding: 0 }` in print so default body margins don't bleed in. (b) For rotated images, position the `<img>` absolutely at `top: 50%; left: 50%; transform: translate(-50%, -50%)`, and **swap** its layout-box dimensions in JS (`width = wrapMM.h`, `height = wrapMM.w`) so the post-rotation visual matches the wrap rectangle and stays centered.
- **Affected files**: `services/frontend/src/styles/global.css`, `services/frontend/src/utils/printDocuments.ts`
- **Commit/PR**: #47 (caught immediately after BUG-006 fix during EDDV multi-print re-test — fixed before merge).

### [BUG-009] Gateway `/api/favorites` returns 500 after pytest run in shared Postgres
- **Symptom**: After running `pytest services/gateway/tests/` against the dev compose stack, `GET /api/favorites` returns 500 with `relation "gateway.favorites" does not exist`, even though `alembic current` still reports `20260516_0002` (head). `\dt gateway.*` confirms the table is gone but `gateway.alembic_version` still says head.
- **Root cause**: `services/gateway/conftest.py` had `Base.metadata.drop_all(bind=engine)` in its session-scoped teardown. The dev pytest run shares the Postgres instance with the running dev stack — when the test session ended, `drop_all` removed `gateway.favorites` from the live DB. Alembic's `alembic_version` is not in `Base.metadata`, so its row stayed at `20260516_0002` and reported a false "head" state. Subsequent gateway requests then hit the missing table.
- **Fix**: Remove `drop_all` from `_prepare_schema` teardown. Per-test isolation is still provided by the `TRUNCATE TABLE gateway.favorites` in the `db_session` fixture. CI starts from a fresh Postgres each run so leaving the table after the test session is harmless there.
- **Recovery**: Reset alembic to baseline (`UPDATE gateway.alembic_version SET version_num='20260419_0001'`) then `alembic upgrade head` to recreate the table.
- **Affected files**: `services/gateway/conftest.py`
- **Commit/PR**: #55 → fix branch `fix/55-conftest-drop-all` (caught during PR #56 housekeeping verification).

### [BUG-008] CI red on every push: Vitest "Cannot find module @rollup/rollup-linux-x64-gnu" + pytest exit 5 on services without tests
- **Symptom**: Every GitHub Actions CI run fails. Email "[DMPlisken/AeroFly] CI workflow run — Some jobs were not successful". `frontend` job dies with `Error: Cannot find module @rollup/rollup-linux-x64-gnu`. `python-services (gateway)` and `python-services (search)` die with `collected 0 items / Process completed with exit code 5`. `python-services (data-ingestion)` shows as Cancelled (would actually pass).
- **Root cause**: Two independent issues compounded by matrix `fail-fast: true`. (1) **npm/cli#4828** — `package-lock.json` is generated on the developer's Windows machine, where npm only locks the `win32-x64-msvc` rollup binary into `optionalDependencies`. `npm ci` on `ubuntu-latest` strictly follows that lockfile and never installs `@rollup/rollup-linux-x64-gnu`, so Rollup crashes loading its native bindings as soon as Vitest starts. (2) **pytest exit code 5** = "no tests collected", returned when a test directory contains only `__init__.py`. CI treats any non-zero exit as failure. `services/gateway/tests/` and `services/search/tests/` had no test files yet; the matrix's default fail-fast cancelled `data-ingestion` before its passing tests could run.
- **Fix**: (a) Add cross-platform rollup binaries (`linux-x64-gnu`, `linux-arm64-gnu`, `darwin-x64`, `darwin-arm64`, `win32-x64-msvc`) to `optionalDependencies` in `services/frontend/package.json` so npm always tries to install the right binary regardless of where the lockfile was generated. (b) In `.github/workflows/ci.yml`, replace the frontend `npm ci` step with `rm -rf node_modules package-lock.json && npm install --no-audit --no-fund` — drops the Windows-locked binaries and lets npm resolve Linux ones fresh. (c) Wrap pytest so exit code 5 is treated as success. (d) Add `fail-fast: false` to the python-services matrix so one service's failure no longer hides the others.
- **Affected files**: `.github/workflows/ci.yml`, `services/frontend/package.json`
- **Commit/PR**: #53 → fix branch `fix/53-ci-workflow-stability`
