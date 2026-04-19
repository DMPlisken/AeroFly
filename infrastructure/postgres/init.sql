-- AeroFly PostgreSQL initialization
--
-- NOTE: Service schemas (`ingest`, `search`, `gateway`) are created by each
-- service's Alembic migration, not here. Keeping this file for future
-- extension installs only.

-- Example for later:
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- fuzzy text search on ICAO/names
-- CREATE EXTENSION IF NOT EXISTS postgis;   -- geographic queries (deferred)
