#!/usr/bin/env bash
# Shared warmup script for Docker containers.
#
# Waits for the inference server to become healthy, then runs warmup tests
# to exercise the model and prime GPU caches. Mirrors scripts/warmup.sh behavior.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

# Configuration
MAX_WAIT="${WARMUP_MAX_WAIT:-300}"
WAIT_INTERVAL="${WARMUP_WAIT_INTERVAL:-5}"
RUN_WARMUP_TESTS="${RUN_WARMUP_TESTS:-1}"
WARMUP_RETRIES="${WARMUP_RETRIES:-2}"

# Paths
ROOT_DIR="${ROOT_DIR:-/app}"
LOG_DIR="${LOG_DIR:-${ROOT_DIR}/logs}"
mkdir -p "${LOG_DIR}"

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

# ============================================================================
# Run warmup tests
# ============================================================================
run_warmup_tests() {
  if [ "${RUN_WARMUP_TESTS}" != "1" ]; then
    log_info "[warmup] Warmup tests disabled (RUN_WARMUP_TESTS=0)"
    return 0
  fi

  # Check if warmup test exists
  local warmup_test="${ROOT_DIR}/tests/warmup.py"
  if [ ! -f "${warmup_test}" ]; then
    log_info "[warmup] No warmup tests found at ${warmup_test}"
    return 0
  fi

  # Find Python
  local py_bin=""
  if [ -x "/opt/venv/bin/python" ]; then
    py_bin="/opt/venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    py_bin="python3"
  elif command -v python >/dev/null 2>&1; then
    py_bin="python"
  else
    log_warn "[warmup] ⚠ No Python interpreter found, skipping warmup tests"
    return 0
  fi

  # Set PYTHONPATH
  export PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"

  log_info "[warmup] Running warmup tests..."

  # Run warmup with retries
  local attempt=1
  local warmup_log="${LOG_DIR}/warmup.log"

  while [ $attempt -le "$WARMUP_RETRIES" ]; do
    log_info "[warmup] Warmup attempt ${attempt}/${WARMUP_RETRIES}"

    if "${py_bin}" "${warmup_test}" >"${warmup_log}" 2>&1; then
      log_success "[warmup] ✓ Warmup done"
      return 0
    fi

    log_warn "[warmup] ⚠ Warmup attempt ${attempt} failed (see ${warmup_log})"
    attempt=$((attempt + 1))
    sleep 2
  done

  log_warn "[warmup] ⚠ Warmup tests failed after ${WARMUP_RETRIES} attempts"
  # Don't fail the container, just warn
  return 0
}

# ============================================================================
# Main execution
# ============================================================================

if wait_for_health; then
  run_warmup_tests
fi
