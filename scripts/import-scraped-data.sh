#!/usr/bin/env bash
# Import the scraped DFS aerodrome data from ./data into the ingest schema.
#
# Usage (project root, stack running, migrations applied):
#   bash scripts/import-scraped-data.sh           # additive (idempotent)
#   bash scripts/import-scraped-data.sh --wipe    # TRUNCATE aerodromes first
#
# Requires ./data to be mounted into the data-ingestion container at /app/data
# (configured in docker-compose.yml).

set -euo pipefail

echo ">>> importing scraped aerodromes from data/"
docker compose exec -T data-ingestion python scripts/import_scraped_data.py "$@"
