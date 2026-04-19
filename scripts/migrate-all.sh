#!/usr/bin/env bash
# Run alembic upgrade head in every service container that owns a schema.
#
# Usage (from the project root, stack must be running):
#   bash scripts/migrate-all.sh
#
# Exit status: non-zero if any migration fails.

set -euo pipefail

services=(data-ingestion search gateway)

for svc in "${services[@]}"; do
  echo ">>> alembic upgrade head [$svc]"
  docker compose exec -T "$svc" alembic upgrade head
done

echo
echo "All migrations applied."
