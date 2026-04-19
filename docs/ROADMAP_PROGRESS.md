# AeroFly — Roadmap & Progress

## Phase 1: Aerodrome Compendium (Current)

### Infrastructure
- [x] Project scaffolding & GitHub setup
- [x] Docker Compose stack (PostgreSQL, Redis, Meilisearch, Nginx)
- [x] CI pipeline (GitHub Actions)
- [x] Database schema design (aerodromes, runways, frequencies, charts, NOTAMs, AIRAC) — issue #4, authoritative `ingest` schema
- [x] Alembic migrations for all services — issue #4, data-ingestion (6 tables + 9 enums), search + gateway (baseline schemas)

### Data Ingestion
- [~] DFS AIP parser — aerodrome directory (AD 2) — **won't do** (issue #10 closed). The chart images already contain the authoritative data; structured extraction would be lossy.
- [~] Runway data extraction (dimensions, surface, orientation) — **won't do** (part of #10). Pilot reads it from the chart.
- [~] Frequency extraction (TWR, GND, ATIS, AFIS) — **won't do** (part of #10). Pilot reads it from the chart.
- [x] Aerodrome chart/map PDF ingestion & indexing — feat/1 scraper (1042 PNGs) + issue #8 importer + issue #13 inline display
- [ ] NOTAM feed integration — issue #12 (pending go/no-go decision)
- [ ] Scheduled re-sync jobs — for future AIRAC-cycle updates via the existing scraper

### Search & API
- [ ] Meilisearch index configuration (aerodromes, frequencies, charts) — issue #11 (pending go/no-go decision)
- [x] Gateway REST API — aerodrome listing + detail endpoints — issue #8
- [x] Full-text prefix search endpoint (ICAO, name) — issue #8 (ILIKE against Postgres)
- [x] Swagger/OpenAPI documentation — gateway at `/api/docs`, data-ingestion at `/docs`
- [x] Chart image serving — issue #13 (nginx serves PNGs directly from data-ingestion volume, 1-day browser cache)
- [~] API authentication (JWT) — **won't do** (issue #14 closed). Data is public.
- [~] Rate limiting — **won't do** for Phase 1. Revisit if third-party API consumers appear.

### Frontend
- [x] Design Kit creation (`docs/Design-Kits/aerofly-design-kit.html`) — v2.0 dark-first glassmorphism, 22 sections incl. 3 page mockups, issue #2
- [x] Aerodrome search page — issue #8, paginated, filterable, Vite proxy to gateway
- [x] Aerodrome detail view — issue #8 + #13 (inline chart images; runway/frequency/NOTAM sections stay "—" since the chart itself contains those)
- [x] Bilingual UI (DE/EN) — issue #8, custom I18nProvider, every string translated, persisted via localStorage
- [ ] Responsive layout — issue #15 (pending go/no-go decision)

## Phase 2: Enhanced Data & Tools (Planned)
- [ ] Weather integration (METAR/TAF)
- [ ] Route planning helper
- [ ] Fuel availability data
- [ ] PPR (Prior Permission Required) tracking
- [ ] API consumer portal with key management

## Phase 3: Mobile Offline App (Planned)
- [ ] iOS app (React Native or native Swift)
- [ ] Android app (React Native or native Kotlin)
- [ ] Offline data sync & caching
- [ ] Offline chart viewer
