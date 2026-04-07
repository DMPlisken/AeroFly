# AeroFly

Aerodrome information compendium for German airports — index, search and serve DFS (Deutsche Flugsicherung) data via API.

## What is AeroFly?

AeroFly provides pilots with all the aerodrome information they need for departure and arrival at German airports:

- **Aerodrome maps & charts** (AD 2 from DFS AIP)
- **Runway data** (dimensions, surface, orientation, lighting)
- **Frequencies** (TWR, GND, ATIS, AFIS, APP)
- **NOTAMs** and operational restrictions
- **Full-text search** across all aerodrome data

All data is served via a documented REST API (Swagger/OpenAPI) for integration with other aviation tools.

## Architecture

Microservices running in Docker:

| Service | Port | Purpose |
|---------|------|---------|
| Gateway | 8000 | API gateway, auth, Swagger docs |
| Data Ingestion | 8001 | DFS data scraping & import |
| Search | 8002 | Full-text search (Meilisearch) |
| Frontend | 3000 | Web UI (React/TypeScript) |
| PostgreSQL | 5432 | Primary data store |
| Redis | 6379 | Cache & pub/sub |
| Meilisearch | 7700 | Search engine |
| Nginx | 80 | Reverse proxy |

## Quick Start

```bash
# 1. Clone
git clone https://github.com/DMPlisken/AeroFly.git
cd AeroFly

# 2. Configure
cp .env.example .env
# Edit .env with your values

# 3. Start
docker compose up --build

# 4. Access
# Web UI:       http://localhost
# API docs:     http://localhost:8000/api/docs
# Meilisearch:  http://localhost:7700
```

## Languages

AeroFly supports German (DE) and English (EN).

## Project Phases

1. **Phase 1** (current): Aerodrome compendium — data ingestion, search, API
2. **Phase 2**: Enhanced data (METAR/TAF, route planning, fuel data)
3. **Phase 3**: Offline mobile apps (iOS/Android)

## License

MIT
