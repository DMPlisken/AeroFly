# AeroFly — Roadmap & Progress

## Phase 1: Aerodrome Compendium (Current)

### Infrastructure
- [x] Project scaffolding & GitHub setup
- [x] Docker Compose stack (PostgreSQL, Redis, Meilisearch, Nginx)
- [x] CI pipeline (GitHub Actions)
- [ ] Database schema design (aerodromes, runways, frequencies, NOTAMs)
- [ ] Alembic migrations for all services

### Data Ingestion
- [ ] DFS AIP parser — aerodrome directory (AD 2)
- [ ] Runway data extraction (dimensions, surface, orientation)
- [ ] Frequency extraction (TWR, GND, ATIS, AFIS)
- [ ] Aerodrome chart/map PDF ingestion & indexing
- [ ] NOTAM feed integration
- [ ] Scheduled re-sync jobs

### Search & API
- [ ] Meilisearch index configuration (aerodromes, frequencies, charts)
- [ ] Gateway REST API — aerodrome CRUD endpoints
- [ ] Full-text search endpoint (ICAO, name, city, region)
- [ ] Swagger/OpenAPI documentation
- [ ] API authentication (JWT)
- [ ] Rate limiting

### Frontend
- [x] Design Kit creation (`docs/Design-Kits/aerofly-design-kit.html`) — v2.0 dark-first glassmorphism, 22 sections incl. 3 page mockups, issue #2
- [ ] Aerodrome search page
- [ ] Aerodrome detail view (map, runways, frequencies, charts)
- [ ] Bilingual UI (DE/EN)
- [ ] Responsive layout

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
