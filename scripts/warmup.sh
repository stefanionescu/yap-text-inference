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
  local timeout_s=180
  local start_ts
  start_ts=$(date +%s)
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
    if (( $(date +%s) - start_ts >= timeout_s )); then
      return 1
    fi
    sleep 2
  done
}

detect_max_conn() {
  "${PY_BIN}" - <<'PY'
from src.config import MAX_CONCURRENT_CONNECTIONS
print(MAX_CONCURRENT_CONNECTIONS)
PY
}

run_py_tool() {
  local log_path="$1"; shift
  if "${PY_BIN}" "$@" >"${log_path}" 2>&1; then
    return 0
  fi
  return 1
}

log "Warmup: waiting for server readiness on ${SERVER_ADDR}..."
if ! wait_for_ready; then
  log "ERROR: Server not ready within timeout."
  rm -f "${DONE_FILE}"
  exit 0
fi

log "Server ready. Running warmup + bench tests against ${SERVER_WS_URL}..."

if ! max_conn="$(detect_max_conn 2>/dev/null)"; then
  max_conn=""
fi
if [[ -z "${max_conn}" || "${max_conn}" =~ [^0-9] ]]; then
  max_conn=8
fi
if (( max_conn <= 0 )); then
  max_conn=8
fi

ok=1

cd "${ROOT_DIR}"

for idx in 1 2; do
  run_log="${LOG_DIR}/warmup_run_${idx}.log"
  if run_py_tool "${run_log}" "${PY_BIN}" "test/warmup.py"; then
    log "OK: warmup run ${idx} (see ${run_log})"
  else
    log "FAIL: warmup run ${idx} (see ${run_log})"
    ok=0
  fi
  sleep 1
done

for idx in 1 2; do
  run_log="${LOG_DIR}/bench_run_${idx}.log"
  if run_py_tool "${run_log}" "${PY_BIN}" "test/bench.py" "--requests" "${max_conn}" "--concurrency" "${max_conn}"; then
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

