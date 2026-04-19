# AeroFly — Roadmap & Progress

## Phase 1: Aerodrome Compendium (Current)

### Infrastructure
- [x] Project scaffolding & GitHub setup
- [x] Docker Compose stack (PostgreSQL, Redis, Meilisearch, Nginx)
- [x] CI pipeline (GitHub Actions)
- [x] Database schema design (aerodromes, runways, frequencies, charts, NOTAMs, AIRAC) — issue #4, authoritative `ingest` schema
- [x] Alembic migrations for all services — issue #4, data-ingestion (6 tables + 9 enums), search + gateway (baseline schemas)

### Data Ingestion
- [ ] DFS AIP parser — aerodrome directory (AD 2)
- [ ] Runway data extraction (dimensions, surface, orientation)
- [ ] Frequency extraction (TWR, GND, ATIS, AFIS)
- [ ] Aerodrome chart/map PDF ingestion & indexing
- [ ] NOTAM feed integration
- [ ] Scheduled re-sync jobs

### Search & API
- [ ] Meilisearch index configuration (aerodromes, frequencies, charts)
- [x] Gateway REST API — aerodrome listing + detail endpoints — issue #8 (interim; moves to Search when Meilisearch lands)
- [x] Full-text prefix search endpoint (ICAO, name, city, region) — issue #8 (ILIKE against Postgres for now)
- [x] Swagger/OpenAPI documentation — gateway at `/api/docs`, data-ingestion at `/docs`
- [ ] API authentication (JWT)
- [ ] Rate limiting

### Frontend
- [x] Design Kit creation (`docs/Design-Kits/aerofly-design-kit.html`) — v2.0 dark-first glassmorphism, 22 sections incl. 3 page mockups, issue #2
- [x] Aerodrome search page — issue #8, paginated, filterable, Vite proxy to gateway
- [x] Aerodrome detail view — issue #8 (runways + frequencies live; map, charts, NOTAMs are placeholders awaiting data)
- [x] Bilingual UI (DE/EN) — issue #8, custom I18nProvider, every string translated, persisted via localStorage
- [ ] Responsive layout — mobile / tablet breakpoints pending

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
