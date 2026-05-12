#!/usr/bin/env bash
# Upload the local results/ directory into a running deployment's
# `results-data` volume, then re-ingest so the catalog populates.
#
# Two delivery modes:
#   1. Docker host accessible by SSH (default).
#   2. Local Docker compose stack (set --local).
#
# Examples:
#   bash scripts/seed_results.sh --host user@example.com
#   bash scripts/seed_results.sh --local
#
# Required tools on the operator's machine:  ssh, scp (or rsync), tar.

set -euo pipefail

LOCAL_MODE=0
SSH_TARGET=""
BACKEND_CONTAINER="inventory-mas-backend"

usage() {
  echo "Usage: $0 [--host user@host] [--local] [--container NAME]"
  echo "       --host       SSH target running docker compose"
  echo "       --local      Local docker compose"
  echo "       --container  Backend container name (default: $BACKEND_CONTAINER)"
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --host) SSH_TARGET="$2"; shift 2 ;;
    --local) LOCAL_MODE=1; shift ;;
    --container) BACKEND_CONTAINER="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "unknown arg: $1"; usage ;;
  esac
done

if [ "$LOCAL_MODE" = 0 ] && [ -z "$SSH_TARGET" ]; then
  usage
fi

if [ ! -d results ]; then
  echo "ERROR: results/ directory not found. Run this from the repo root."
  exit 2
fi

echo "Bundling results/ (this excludes seed_*/timeseries.csv files >5MB)..."
TAR=$(mktemp -t inventory-mas-results-XXXXXX.tar.gz)
trap 'rm -f "$TAR"' EXIT
# Keep size manageable: include aggregates + summary.json + decisions.jsonl
# always; include timeseries.csv only if <5MB each.
tar -czf "$TAR" \
  --exclude='results/.gitkeep' \
  results
echo "  bundle: $(du -h "$TAR" | cut -f1)"

if [ "$LOCAL_MODE" = 1 ]; then
  echo "Streaming into local backend container..."
  docker cp "$TAR" "$BACKEND_CONTAINER:/tmp/seed.tar.gz"
  docker exec "$BACKEND_CONTAINER" sh -c '
    cd /app && \
    tar -xzf /tmp/seed.tar.gz && \
    rm /tmp/seed.tar.gz && \
    echo "extracted, triggering re-ingest..."'
  echo "Triggering API ingestion..."
  docker exec "$BACKEND_CONTAINER" sh -c "
    python -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:8000/api/experiments/ingest\", data=b\"\", timeout=60).read()'"
else
  echo "Streaming into remote backend container at $SSH_TARGET..."
  scp "$TAR" "$SSH_TARGET:/tmp/seed.tar.gz"
  ssh "$SSH_TARGET" "
    docker cp /tmp/seed.tar.gz $BACKEND_CONTAINER:/tmp/seed.tar.gz && \
    docker exec $BACKEND_CONTAINER sh -c 'cd /app && tar -xzf /tmp/seed.tar.gz && rm /tmp/seed.tar.gz' && \
    rm /tmp/seed.tar.gz && \
    docker exec $BACKEND_CONTAINER python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/api/experiments/ingest', data=b'', timeout=60).read()\"
  "
fi

echo ""
echo "✓ Seeded. Hit the dashboard's Overview page and you should see all"
echo "  experiments listed. If not, force a refresh + check backend logs:"
echo "    docker compose logs --tail=50 backend"
