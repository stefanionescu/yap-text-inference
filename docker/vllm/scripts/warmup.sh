#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

# Warmup script - waits for server to be ready and runs initial validation

MAX_WAIT=300
WAIT_INTERVAL=5
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
  if curl -sf http://localhost:8000/healthz >/dev/null 2>&1; then
    log_success "[vllm-warmup] ✓ Server is healthy after ${ELAPSED}s"
    break
  fi
  sleep $WAIT_INTERVAL
  ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
  log_warn "[vllm-warmup] ⚠ Server did not become healthy within ${MAX_WAIT}s"
  exit 0
fi

log_success "[warmup] ✓ Ready"

