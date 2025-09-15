#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Start Temporal + Postgres + Web
docker compose -f compose.yaml up -d

echo "⏳ Waiting for Postgres to be healthy..."
until docker exec temporal-postgresql pg_isready -U temporal -d temporal >/dev/null 2>&1; do
  sleep 1
done

echo "✅ Postgres ready, applying schema..."
docker cp ../schema.sql temporal-postgresql:/tmp/schema.sql
docker exec temporal-postgresql psql -U temporal -d temporal -f /tmp/schema.sql -v ON_ERROR_STOP=1

echo "🚀 Infra ready:"
echo "- Temporal gRPC: 127.0.0.1:7233"
echo "- Temporal Web UI: http://127.0.0.1:8080"

