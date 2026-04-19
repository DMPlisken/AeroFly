#!/usr/bin/env bash
# Seed 10 real German airports into the ingest schema.
#
# Usage (project root, stack running + migrations applied):
#   bash scripts/seed-demo-data.sh
#
# Idempotent — rerunning skips aerodromes that already exist.

set -euo pipefail

echo ">>> seeding demo aerodromes"
docker compose exec -T data-ingestion python scripts/seed_demo_data.py
