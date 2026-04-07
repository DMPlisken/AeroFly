# AeroFly — Architecture Overview

## System Architecture

AeroFly is a **microservices application** — each functional module runs in its own Docker container, communicating via REST (through the Gateway) and Redis pub/sub.

```
┌─────────────────────────────────────────────────────┐
│                     Nginx (Port 80)                 │
│              Reverse Proxy & Load Balancer           │
└──────────┬──────────────────────────┬───────────────┘
           │                          │
    /api/* │                     /* (SPA)
           ▼                          ▼
┌──────────────────┐      ┌───────────────────┐
│  Gateway :8000   │      │  Frontend :3000   │
│  (FastAPI)       │      │  (React/Vite)     │
│  Auth, Routing,  │      │  Search UI,       │
│  Swagger/OpenAPI │      │  Aerodrome Views  │
└──┬───────┬───────┘      └───────────────────┘
   │       │
   ▼       ▼
┌────────────────┐  ┌─────────────────┐
│ Data Ingestion │  │  Search :8002   │
│ :8001          │  │  (Meilisearch   │
│ DFS scraping,  │  │   client)       │
│ PDF parsing,   │  └────────┬────────┘
│ data import    │           │
└───────┬────────┘           ▼
        │            ┌───────────────┐
        ▼            │  Meilisearch  │
┌───────────────┐    │  :7700        │
│  PostgreSQL   │    │  Full-text    │
│  :5432        │    │  search index │
│  Primary data │    └───────────────┘
│  store        │
└───────────────┘
        ▲
        │
┌───────────────┐
│  Redis :6379  │
│  Cache &      │
│  Pub/Sub      │
└───────────────┘
```

## Data Flow

1. **Data Ingestion** scrapes DFS AIP data (aerodrome info, charts, frequencies, runways) and stores it in PostgreSQL.
2. **Data Ingestion** publishes update events via Redis pub/sub.
3. **Search** service listens for updates and syncs data into Meilisearch indexes.
4. **Gateway** exposes REST API with Swagger docs at `/api/docs`.
5. **Frontend** provides the web UI for searching and viewing aerodrome data.

## Service Boundaries

| Service | Responsibility | Does NOT do |
|---------|---------------|-------------|
| Gateway | Auth, routing, API aggregation, Swagger | Direct DB queries for domain data |
| Data Ingestion | DFS scraping, PDF parsing, DB writes | Serving search results |
| Search | Meilisearch indexing & querying | Data scraping, DB writes |
| Frontend | UI rendering, user interaction | Direct backend DB access |

## Database Strategy

- **PostgreSQL 16** — Primary data store. Each service that needs persistence gets its own schema.
- **Meilisearch** — Full-text search engine. Fed by the Search service from PostgreSQL data.
- **Redis 7** — Caching layer and inter-service pub/sub messaging.

## Bilingual Support (DE/EN)

- API responses include both `name` (English) and `name_de` (German) fields where applicable.
- Frontend uses i18n with language toggle.
- Search indexes are configured for both German and English tokenization.
