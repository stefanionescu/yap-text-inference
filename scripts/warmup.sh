#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source venv helpers, logging, and env defaults
source "${SCRIPT_DIR}/lib/deps/venv.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/common/log.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/env/runtime.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/env/server.sh" 2>/dev/null || true
source "${SCRIPT_DIR}/lib/env/warmup.sh" 2>/dev/null || true

runtime_init_repo_paths "${ROOT_DIR}"
server_init_network_defaults
warmup_init_defaults "${ROOT_DIR}" "${SCRIPT_DIR}"

log_warmup() {
  local line="[warmup] $*"
  log_info "${line}"
  echo "${line}" >> "${WARMUP_LOG_FILE}"
}

write_lock() {
  echo "$$" > "${WARMUP_LOCK_FILE}"
}

# shellcheck disable=SC2329
cleanup_lock() {
  rm -f "${WARMUP_LOCK_FILE}" || true
}

choose_python() {
  local venv_py=""
  if command -v get_venv_python >/dev/null 2>&1; then
    venv_py="$(get_venv_python 2>/dev/null || true)"
  elif command -v get_venv_dir >/dev/null 2>&1; then
    local fallback_dir
    fallback_dir="$(get_venv_dir)"
    venv_py="${fallback_dir}/bin/python"
  fi
  if [ -n "${venv_py}" ] && [ -x "${venv_py}" ]; then
    echo "${venv_py}"
    return 0
  fi

  if command -v get_python_binary_for_engine >/dev/null 2>&1; then
    local engine_py
    engine_py="$(get_python_binary_for_engine 2>/dev/null || true)"
    if [ -n "${engine_py}" ] && command -v "${engine_py}" >/dev/null 2>&1; then
      command -v "${engine_py}"
      return 0
    fi
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
  local urls=("${SERVER_HEALTH_URLS[@]}")
  while (( SECONDS <= deadline )); do
    if bash "${WARMUP_HEALTH_CHECK_SCRIPT}" "${urls[@]}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${WARMUP_HEALTH_POLL_INTERVAL_SECS}"
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
  log_warmup "MAX_CONCURRENT_CONNECTIONS not set or invalid, defaulting to ${WARMUP_DEFAULT_CONN_FALLBACK}"
  max_conn="${WARMUP_DEFAULT_CONN_FALLBACK}"
fi
if (( max_conn <= 0 )); then
  log_warmup "MAX_CONCURRENT_CONNECTIONS is <= 0, defaulting to ${WARMUP_DEFAULT_CONN_FALLBACK}"
  max_conn="${WARMUP_DEFAULT_CONN_FALLBACK}"
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
  sleep "${WARMUP_RUN_DELAY_SECS}"
done

for (( idx=1; idx<=WARMUP_RETRIES; idx++ )); do
  run_log="${LOG_DIR}/bench_run_${idx}.log"
  if run_py_tool "${run_log}" "tests/bench.py" "${PROMPT_MODE_FLAGS[@]}" "--requests" "${max_conn}" "--concurrency" "${max_conn}"; then
    log_warmup "OK: bench run ${idx} (n=${max_conn}, c=${max_conn}) (see ${run_log})"
  else
    log_warmup "✗ FAIL: bench run ${idx} (see ${run_log})"
    ok=0
  fi
  sleep "${WARMUP_RUN_DELAY_SECS}"
done

if [[ "${ok}" -eq 1 ]]; then
  log_warmup "✓ Warmup + bench complete."
  exit 0
fi

log_warmup "Warmup finished with failures."
exit 1
