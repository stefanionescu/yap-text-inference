#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# GPU Warmup and Benchmark Script
# =============================================================================
# Runs warmup and benchmark tests against the running server to validate
# deployment health. Supports multiple persona variants and tracks pass/fail
# results for each phase.
#
# Usage: bash scripts/warmup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source venv helpers, logging, and env defaults
source "${SCRIPT_DIR}/lib/deps/venv.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/noise/python.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/common/log.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/common/string.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/env/runtime.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/env/server.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/env/warmup.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/runtime/warmup_runner.sh" 2>/dev/null || true

runtime_init_repo_paths "${ROOT_DIR}"
init_network_defaults
init_warmup_defaults "${ROOT_DIR}" "${SCRIPT_DIR}"

declare -a WARMUP_PERSONA_VARIANTS=()

# =============================================================================
# LOCK MANAGEMENT
# =============================================================================

write_lock() {
  echo "$$" >"${WARMUP_LOCK_FILE}"
}

# shellcheck disable=SC2329
cleanup_lock() {
  rm -f "${WARMUP_LOCK_FILE}" || true
}

# =============================================================================
# INITIALIZATION
# =============================================================================

# Activate venv if available (non-fatal)
activate_venv "" 0 || true

if ! PY_BIN="$(warmup_choose_python)"; then
  warmup_log_phase_result "startup" "FAIL"
  log_info "[warmup] ✗ Unable to locate python interpreter."
  exit 1
fi

PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONPATH

write_lock
trap cleanup_lock EXIT INT TERM

# =============================================================================
# CONFIGURATION
# =============================================================================

max_conn="$(warmup_detect_max_conn "${PY_BIN}" "${ROOT_DIR}" "${WARMUP_DEFAULT_CONN_FALLBACK}")" || true
if [[ -z ${max_conn} || ${max_conn} =~ [^0-9] ]]; then
  warmup_log_internal "MAX_CONCURRENT_CONNECTIONS not set or invalid, defaulting to ${WARMUP_DEFAULT_CONN_FALLBACK}"
  max_conn="${WARMUP_DEFAULT_CONN_FALLBACK}"
fi
if ((max_conn <= 0)); then
  warmup_log_internal "MAX_CONCURRENT_CONNECTIONS is <= 0, defaulting to ${WARMUP_DEFAULT_CONN_FALLBACK}"
  max_conn="${WARMUP_DEFAULT_CONN_FALLBACK}"
fi

warmup_log_internal "Using MAX_CONCURRENT_CONNECTIONS=${max_conn} for benchmark tests"

warmup_all_passed=1

warmup_detect_persona_variants "${PY_BIN}"
for persona in "${WARMUP_PERSONA_VARIANTS[@]}"; do
  IFS='|' read -r persona_gender persona_personality <<<"${persona}"
  warmup_log_internal "Persona variant configured: gender=${persona_gender:-default} personality=${persona_personality:-}"
done

cd "${ROOT_DIR}"

# =============================================================================
# MAIN TEST LOOP
# =============================================================================

# Small delay to let Uvicorn's buffered output flush before warmup messages
sleep 0.1
echo # Blank line to stdout (log_blank goes to stderr, can get interleaved)
log_info "[warmup] Starting GPU warmup..."
echo "[warmup] Starting GPU warmup..." >>"${ROOT_DIR}/server.log"

for persona in "${WARMUP_PERSONA_VARIANTS[@]}"; do
  IFS='|' read -r persona_gender persona_personality <<<"${persona}"
  persona_gender="$(str_trim "${persona_gender}")"
  persona_personality="$(str_trim "${persona_personality}")"
  persona_label="${persona_gender:-default}"

  persona_args=()
  if [ -n "${persona_gender}" ]; then
    persona_args+=("--gender" "${persona_gender}")
  fi
  if [ -n "${persona_personality}" ]; then
    persona_args+=("--personality" "${persona_personality}")
  fi

  warmup_label="warmup: ${persona_label}"
  warmup_prefix="$(warmup_safe_log_prefix "warmup_${persona_label}")"
  if ! warmup_run_with_retries \
    "${warmup_label}" \
    "${warmup_prefix}" \
    "${PY_BIN}" \
    "${LOG_DIR}" \
    "${WARMUP_RETRIES}" \
    "tests/e2e/warmup.py" "${persona_args[@]}"; then
    warmup_all_passed=0
  fi
  sleep "${WARMUP_RUN_DELAY_SECS}"

  bench_label="warmup: bench ${max_conn}x ${persona_label}"
  bench_prefix="$(warmup_safe_log_prefix "bench_${max_conn}x_${persona_label}")"
  if ! warmup_run_with_retries \
    "${bench_label}" \
    "${bench_prefix}" \
    "${PY_BIN}" \
    "${LOG_DIR}" \
    "${WARMUP_RETRIES}" \
    "tests/e2e/bench.py" \
    "--requests" "${max_conn}" \
    "--concurrency" "${max_conn}" \
    "${persona_args[@]}"; then
    warmup_all_passed=0
  fi
  sleep "${WARMUP_RUN_DELAY_SECS}"
done

# =============================================================================
# RESULT REPORTING
# =============================================================================

if [[ ${warmup_all_passed} -eq 1 ]]; then
  log_info "[warmup] ✓ Warmup complete."
  echo "[warmup] ✓ Warmup complete." >>"${ROOT_DIR}/server.log"
  exit 0
fi

log_info "[warmup] Warmup finished with failures."
echo "[warmup] Warmup finished with failures." >>"${ROOT_DIR}/server.log"
exit 1
