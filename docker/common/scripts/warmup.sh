#!/usr/bin/env bash
# shellcheck disable=SC1091
# Shared warmup script for Docker containers.
#
# Waits for the inference server to become healthy before returning. This does
# not execute test clients inside Docker.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

# Configuration
MAX_WAIT="${WARMUP_MAX_WAIT:-300}"
WAIT_INTERVAL="${WARMUP_WAIT_INTERVAL:-5}"

# ============================================================================
# Wait for server health
# ============================================================================
wait_for_health() {
  local elapsed=0

  log_info "[warmup] Waiting for server to become healthy..."

  while [ $elapsed -lt "$MAX_WAIT" ]; do
    if curl -sf http://localhost:8000/healthz >/dev/null 2>&1; then
      log_success "[warmup] ✓ Server is healthy after ${elapsed}s"
      return 0
    fi
    sleep "$WAIT_INTERVAL"
    elapsed=$((elapsed + WAIT_INTERVAL))
  done

  log_warn "[warmup] ⚠ Server did not become healthy within ${MAX_WAIT}s"
  return 1
}

if wait_for_health; then
  log_success "[warmup] ✓ Warmup health check complete"
fi
