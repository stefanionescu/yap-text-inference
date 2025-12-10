#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
RUN_DIR="${ROOT_DIR}/.run"
mkdir -p "${LOG_DIR}" "${RUN_DIR}"

LOG_FILE="${LOG_DIR}/warmup.log"
LOCK_FILE="${RUN_DIR}/warmup.lock"
DONE_FILE="${RUN_DIR}/warmup.done"

if [ -f "${LOCK_FILE}" ]; then
  existing_pid="$(cat "${LOCK_FILE}" 2>/dev/null || true)"
  if [ -n "${existing_pid}" ] && ps -p "${existing_pid}" >/dev/null 2>&1; then
    echo "[warmup] Another warmup run is already in progress (pid=${existing_pid}); skipping." | tee -a "${LOG_FILE}"
    exit 0
  fi
fi

trap 'rm -f "${LOCK_FILE}"' EXIT
echo "$$" > "${LOCK_FILE}"

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

is_tool_model_classifier() {
  # Check if TOOL_MODEL is a classifier (regardless of deploy mode)
  if "${PY_BIN}" -c "
import sys
sys.path.insert(0, '${ROOT_DIR}')
from src.config import is_classifier_model, TOOL_MODEL
sys.exit(0 if is_classifier_model(TOOL_MODEL) else 1)
" 2>/dev/null; then
    return 0  # Tool model is a classifier
  fi
  return 1  # Tool model is not a classifier
}

is_classifier_only_mode() {
  # Check if we're in classifier-only mode (no vLLM warmup needed at all)
  local deploy_mode="${DEPLOY_MODELS:-}"
  if [[ "${deploy_mode}" != "tool" ]]; then
    return 1  # Not tool-only mode
  fi
  # Tool-only mode with classifier = no vLLM engines at all
  is_tool_model_classifier
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

# Skip warmup tests for classifier-only mode (classifier loads lazily, no vLLM to warm)
if is_classifier_only_mode; then
  log "Classifier-only mode detected (DEPLOY_MODELS=tool, TOOL_MODEL is classifier)"
  log "Skipping warmup tests - classifier initializes on first request"
  echo "done" > "${DONE_FILE}"
  exit 0
fi

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
PROMPT_MODE_FLAG=(--prompt-mode "${prompt_mode}")
log "Using prompt mode '${prompt_mode}' for warmup + bench tests"

# Detect if tool model is a classifier (don't send tool_prompt in tests)
CLASSIFIER_MODE_FLAG=()
if is_tool_model_classifier; then
  CLASSIFIER_MODE_FLAG=(--classifier-mode)
  log "Tool model is a classifier - tests will not send tool_prompt"
fi

cd "${ROOT_DIR}"

for idx in 1 2; do
  run_log="${LOG_DIR}/warmup_run_${idx}.log"
  if run_py_tool "${run_log}" "tests/warmup.py" "${PROMPT_MODE_FLAG[@]}" "${CLASSIFIER_MODE_FLAG[@]}"; then
    log "OK: warmup run ${idx} (see ${run_log})"
  else
    log "FAIL: warmup run ${idx} (see ${run_log})"
    ok=0
  fi
  sleep 1
done

for idx in 1 2; do
  run_log="${LOG_DIR}/bench_run_${idx}.log"
  if run_py_tool "${run_log}" "tests/bench.py" "${PROMPT_MODE_FLAG[@]}" "${CLASSIFIER_MODE_FLAG[@]}" "--requests" "${max_conn}" "--concurrency" "${max_conn}"; then
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

echo "done" > "${DONE_FILE}"
exit 0

