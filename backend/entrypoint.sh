#!/bin/sh
# Backend container entrypoint.
#
# Why this exists:
#   The image bundles the canonical thesis results at /app/results-baseline.
#   At runtime, /app/results is a Docker named volume (`results-data`) so
#   user-generated runs persist across re-deploys. But Docker only auto-
#   populates a named volume from the image *when the volume is first
#   created* — empty pre-existing volumes (e.g. from earlier deploys) stay
#   empty, and image updates with new baseline results don't propagate.
#
# This script reconciles both cases on every start using `cp -rn` (no-
# clobber): baseline files appear in the volume, user-generated runs are
# never overwritten, and re-deploys with updated baselines merge cleanly.

set -e

if [ -d "/app/results-baseline" ]; then
    echo "[entrypoint] Seeding canonical results from baseline (no-clobber)..."
    mkdir -p /app/results
    cp -rn /app/results-baseline/. /app/results/ || true
    echo "[entrypoint] /app/results now contains:"
    ls /app/results/ | head -20
fi

exec "$@"
