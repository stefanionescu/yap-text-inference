#!/usr/bin/env bash
# Shared warmup script for Docker containers.
#
# Waits for the inference server to become healthy, then exits. Used by both
# TRT and vLLM containers during startup. Accepts an optional engine prefix
# for log messages.
#
# Usage: warmup.sh [engine_prefix]
#   engine_prefix: Optional prefix for log messages (default: "container")

set -euo pipefail

ENGINE_PREFIX="${1:-container}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

MAX_WAIT=300
WAIT_INTERVAL=5
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
  if curl -sf http://localhost:8000/healthz >/dev/null 2>&1; then
    log_success "[${ENGINE_PREFIX}-warmup] ✓ Server is healthy after ${ELAPSED}s"
    break
  fi
  sleep $WAIT_INTERVAL
  ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
  log_warn "[${ENGINE_PREFIX}-warmup] ⚠ Server did not become healthy within ${MAX_WAIT}s"
  exit 0
fi

log_success "[warmup] ✓ Ready"

