#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
RUN_DIR="${ROOT_DIR}/.run"
LOG_FILE="${LOG_DIR}/warmup.log"
LOCK_FILE="${RUN_DIR}/warmup.lock"
HEALTH_CHECK_SCRIPT="${SCRIPT_DIR}/lib/common/health.sh"
mkdir -p "${LOG_DIR}" "${RUN_DIR}"

# Source venv helpers and logging (needed for log_err in helpers)
source "${SCRIPT_DIR}/lib/deps/venv.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/common/log.sh" 2>/dev/null || true

HOST_VAL="${HOST:-127.0.0.1}"
PORT_VAL="${PORT:-8000}"
SERVER_ADDR="${HOST_VAL}:${PORT_VAL}"
SERVER_WS_URL="${SERVER_WS_URL:-ws://${SERVER_ADDR}/ws}"
HEALTH_URLS=("http://${SERVER_ADDR}/healthz" "http://${SERVER_ADDR}/health")
WARMUP_TIMEOUT_SECS="${WARMUP_TIMEOUT_SECS:-300}"
if ! [[ "${WARMUP_TIMEOUT_SECS}" =~ ^[0-9]+$ ]] || (( WARMUP_TIMEOUT_SECS < 1 )); then
  WARMUP_TIMEOUT_SECS=300
fi
WARMUP_RETRIES="${WARMUP_RETRIES:-2}"
if ! [[ "${WARMUP_RETRIES}" =~ ^[0-9]+$ ]] || (( WARMUP_RETRIES < 1 )); then
  WARMUP_RETRIES=2
fi
export SERVER_WS_URL

log_warmup() {
  local line="[warmup] $*"
  log_info "${line}"
  echo "${line}" >> "${LOG_FILE}"
}

write_lock() {
  echo "$$" > "${LOCK_FILE}"
}

# shellcheck disable=SC2329
cleanup_lock() {
  rm -f "${LOCK_FILE}" || true
}

choose_python() {
  local venv_dir
  if command -v get_venv_dir >/dev/null 2>&1; then
    venv_dir="$(get_venv_dir)"
  else
    venv_dir="${ROOT_DIR}/.venv"
  fi
  local venv_py="${venv_dir}/bin/python"
  if [ -x "${venv_py}" ]; then
    echo "${venv_py}"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  return 1
}

# Activate venv if available (non-fatal)
activate_venv "" 0 || true

if ! PY_BIN="$(choose_python)"; then
  log_warmup "✗ Unable to locate python interpreter."
  exit 1
fi

PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONPATH

wait_for_ready() {
  local deadline=$((SECONDS + WARMUP_TIMEOUT_SECS))
  local urls=("${HEALTH_URLS[@]}")
  while (( SECONDS <= deadline )); do
    if bash "${HEALTH_CHECK_SCRIPT}" "${urls[@]}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

detect_max_conn() {
  if [[ -n "${MAX_CONCURRENT_CONNECTIONS:-}" ]]; then
    echo "${MAX_CONCURRENT_CONNECTIONS}"
    return 0
  fi

  local py_output
  if py_output="$("${PY_BIN}" -c "
import sys
import os
sys.path.insert(0, '${ROOT_DIR}')
from src.config.limits import MAX_CONCURRENT_CONNECTIONS
print(MAX_CONCURRENT_CONNECTIONS)
" 2>/dev/null)"; then
    if [[ -n "${py_output}" && "${py_output}" =~ ^[0-9]+$ ]]; then
      echo "${py_output}"
      return 0
    fi
  fi

  return 1
}

detect_prompt_mode() {
  local deploy_mode="${DEPLOY_MODE:-}"
  case "${deploy_mode}" in
    chat) echo "chat"; return 0 ;;
    tool) echo "tool"; return 0 ;;
  esac

  local chat_flag="${DEPLOY_CHAT:-}"
  local tool_flag="${DEPLOY_TOOL:-}"
  if [[ "${chat_flag}" = "1" && "${tool_flag}" = "1" ]]; then
    echo "both"
  elif [[ "${chat_flag}" = "1" ]]; then
    echo "chat"
  elif [[ "${tool_flag}" = "1" ]]; then
    echo "tool"
  else
    echo "both"
  fi
}

run_py_tool() {
  local log_path="$1"; shift
  if "${PY_BIN}" "$@" >"${log_path}" 2>&1; then
    return 0
  fi
  return 1
}

write_lock
trap cleanup_lock EXIT INT TERM

log_warmup "Waiting for server readiness on ${SERVER_ADDR} (timeout ${WARMUP_TIMEOUT_SECS}s)..."
if ! wait_for_ready; then
  log_warmup "✗ Server did not become healthy within ${WARMUP_TIMEOUT_SECS}s"
  exit 1
fi

log_warmup "Server ready. Running warmup + bench tests against ${SERVER_WS_URL}..."

if ! max_conn="$(detect_max_conn)"; then
  max_conn=""
fi
if [[ -z "${max_conn}" || "${max_conn}" =~ [^0-9] ]]; then
  log_warmup "MAX_CONCURRENT_CONNECTIONS not set or invalid, defaulting to 8"
  max_conn=8
fi
if (( max_conn <= 0 )); then
  log_warmup "MAX_CONCURRENT_CONNECTIONS is <= 0, defaulting to 8"
  max_conn=8
fi

log_warmup "Using MAX_CONCURRENT_CONNECTIONS=${max_conn} for benchmark tests"

ok=1
prompt_mode="$(detect_prompt_mode)"
PROMPT_MODE_FLAGS=()
if [[ "${prompt_mode}" == "tool" ]]; then
  PROMPT_MODE_FLAGS=(--no-chat-prompt)
fi
log_warmup "Using prompt mode '${prompt_mode}' for warmup + bench tests"

cd "${ROOT_DIR}"

for (( idx=1; idx<=WARMUP_RETRIES; idx++ )); do
  run_log="${LOG_DIR}/warmup_run_${idx}.log"
  if run_py_tool "${run_log}" "tests/warmup.py" "${PROMPT_MODE_FLAGS[@]}"; then
    log_warmup "OK: warmup run ${idx} (see ${run_log})"
  else
    log_warmup "✗ FAIL: warmup run ${idx} (see ${run_log})"
    ok=0
  fi
  sleep 1
done

for (( idx=1; idx<=WARMUP_RETRIES; idx++ )); do
  run_log="${LOG_DIR}/bench_run_${idx}.log"
  if run_py_tool "${run_log}" "tests/bench.py" "${PROMPT_MODE_FLAGS[@]}" "--requests" "${max_conn}" "--concurrency" "${max_conn}"; then
    log_warmup "OK: bench run ${idx} (n=${max_conn}, c=${max_conn}) (see ${run_log})"
  else
    log_warmup "✗ FAIL: bench run ${idx} (see ${run_log})"
    ok=0
  fi
  sleep 1
done

if [[ "${ok}" -eq 1 ]]; then
  log_warmup "✓ Warmup + bench complete."
  exit 0
fi

log_warmup "Warmup finished with failures."
exit 1
