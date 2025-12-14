#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "${LOG_DIR}"

LOG_FILE="${LOG_DIR}/warmup.log"

log() {
  local line
  line="[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*"
  echo "${line}" | tee -a "${LOG_FILE}"
}

HOST_VAL="${HOST:-127.0.0.1}"
PORT_VAL="${PORT:-8000}"
SERVER_ADDR="${HOST_VAL}:${PORT_VAL}"
SERVER_WS_URL="${SERVER_WS_URL:-ws://${SERVER_ADDR}/ws}"
export SERVER_WS_URL

HEALTH_URLS=("http://${SERVER_ADDR}/healthz" "http://${SERVER_ADDR}/health")

if [ -d "${ROOT_DIR}/.venv" ]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.venv/bin/activate" || true
fi

if [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
  PY_BIN="${ROOT_DIR}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PY_BIN="$(command -v python)"
else
  log "ERROR: Unable to locate python interpreter."
  exit 1
fi

PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONPATH

wait_for_ready() {
  while true; do
    if "${PY_BIN}" - "${HEALTH_URLS[@]}" <<'PY' >/dev/null 2>&1; then
import sys
import urllib.request

def check(urls):
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            continue
    return False

raise SystemExit(0 if check(sys.argv[1:]) else 1)
PY
      return 0
    fi
    sleep 2
  done
}

detect_max_conn() {
  # First check environment variable directly
  if [[ -n "${MAX_CONCURRENT_CONNECTIONS:-}" ]]; then
    echo "${MAX_CONCURRENT_CONNECTIONS}"
    return 0
  fi
  
  # Fallback: try to read from Python config (requires env var to be set for Python too)
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
  local deploy_mode="${DEPLOY_MODELS:-}"
  case "${deploy_mode}" in
    chat) echo "chat"; return 0 ;;
    tool) echo "tool"; return 0 ;;
    both|"") ;;
    *) ;;
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

log "Warmup: waiting for server readiness on ${SERVER_ADDR}..."
wait_for_ready

log "Server ready. Running warmup + bench tests against ${SERVER_WS_URL}..."

if ! max_conn="$(detect_max_conn)"; then
  max_conn=""
fi
if [[ -z "${max_conn}" || "${max_conn}" =~ [^0-9] ]]; then
  log "WARNING: MAX_CONCURRENT_CONNECTIONS not set or invalid, defaulting to 8"
  max_conn=8
fi
if (( max_conn <= 0 )); then
  log "WARNING: MAX_CONCURRENT_CONNECTIONS is <= 0, defaulting to 8"
  max_conn=8
fi

log "Using MAX_CONCURRENT_CONNECTIONS=${max_conn} for benchmark tests"

ok=1
prompt_mode="$(detect_prompt_mode)"

# Build flags based on prompt mode - use --no-chat-prompt for tool-only deployments
PROMPT_MODE_FLAGS=()
if [[ "${prompt_mode}" == "tool" ]]; then
  PROMPT_MODE_FLAGS=(--no-chat-prompt)
fi
log "Using prompt mode '${prompt_mode}' for warmup + bench tests"

cd "${ROOT_DIR}"

for idx in 1 2; do
  run_log="${LOG_DIR}/warmup_run_${idx}.log"
  if run_py_tool "${run_log}" "tests/warmup.py" "${PROMPT_MODE_FLAGS[@]}"; then
    log "OK: warmup run ${idx} (see ${run_log})"
  else
    log "FAIL: warmup run ${idx} (see ${run_log})"
    ok=0
  fi
  sleep 1
done

for idx in 1 2; do
  run_log="${LOG_DIR}/bench_run_${idx}.log"
  if run_py_tool "${run_log}" "tests/bench.py" "${PROMPT_MODE_FLAGS[@]}" "--requests" "${max_conn}" "--concurrency" "${max_conn}"; then
    log "OK: bench run ${idx} (n=${max_conn}, c=${max_conn}) (see ${run_log})"
  else
    log "FAIL: bench run ${idx} (see ${run_log})"
    ok=0
  fi
  sleep 1
done

if [[ "${ok}" -eq 1 ]]; then
  log "SUCCESS: warmup + bench complete."
else
  log "COMPLETE: warmup finished with failures."
fi

exit 0

