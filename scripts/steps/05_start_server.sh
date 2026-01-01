#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repo root is two levels up from steps/
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${SCRIPT_DIR}/../lib/noise/python.sh"
source "${SCRIPT_DIR}/../lib/common/log.sh"
source "${SCRIPT_DIR}/../lib/runtime/restart_guard.sh"
source "${SCRIPT_DIR}/../lib/deps/venv.sh"
source "${SCRIPT_DIR}/../engines/trt/detect.sh"
source "${SCRIPT_DIR}/../lib/common/cuda.sh"
source "${SCRIPT_DIR}/../lib/env/server.sh"
source "${SCRIPT_DIR}/../lib/env/warmup.sh"

# Validate CUDA 13.x for TRT before starting server
ensure_cuda_ready_for_engine "server" || exit 1

server_init_network_defaults
warmup_init_defaults "${ROOT_DIR}" "${SCRIPT_DIR}/.."

# Wait for server health with timeout. Exits with error if not healthy in time.
wait_for_server_health() {
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

log_info "[server] Starting server on ${SERVER_BIND_ADDR} in background"
cd "${ROOT_DIR}"
# Activate venv if available (non-fatal)
activate_venv "" 0 || true

# Resolve venv directory once for consistent use
VENV_DIR="$(get_venv_dir)"

# Double-start guard and stale PID handling
PID_FILE="${ROOT_DIR}/server.pid"
if [ -f "${PID_FILE}" ]; then
  OLD_PID="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [ -n "${OLD_PID}" ] && ps -p "${OLD_PID}" >/dev/null 2>&1; then
    log_warn "[server] ⚠ Server already running (PID=${OLD_PID}). Aborting start."
    exit 1
  else
    log_warn "[server] ⚠ Stale PID file found; removing ${PID_FILE}"
    rm -f "${PID_FILE}" || true
  fi
fi

# Log key env knobs
if [ "${DEPLOY_MODE:-both}" = "both" ]; then
  log_info "[server]   CHAT=${CHAT_MODEL:-}"
  log_info "[server]   TOOL=${TOOL_MODEL:-}"
elif [ "${DEPLOY_MODE:-both}" = "chat" ]; then
  log_info "[server]   MODEL=${CHAT_MODEL:-}"
else
  log_info "[server]   MODEL=${TOOL_MODEL:-}"
fi

if [ "${DEPLOY_MODE:-both}" = "tool" ]; then
  log_info "[server]   QUANT_MODE=tool-only (classifier-only)"
else
  log_info "[server]   QUANT_MODE=${QUANT_MODE:-auto}"
  log_info "[server]   BACKEND=${QUANTIZATION:-}"
  log_info "[server]   KV_DTYPE=${KV_DTYPE:-}"
fi

log_blank
runtime_guard_write_snapshot "${ROOT_DIR}"

# Resolve uvicorn launcher robustly (prefer venv python -m, then venv binary, then system)
CMD_ARGS=(
  "src.server:app"
  "--host" "${SERVER_BIND_HOST}"
  "--port" "${SERVER_PORT}"
  "--workers" "1"
)

if [ -x "${VENV_DIR}/bin/python" ] && "${VENV_DIR}/bin/python" - <<'PY' >/dev/null 2>&1
import uvicorn
PY
then
  # Prefer venv python -m uvicorn to ensure correct Python interpreter
  CMD=("${VENV_DIR}/bin/python" "-m" "uvicorn" "${CMD_ARGS[@]}")
elif [ -x "${VENV_DIR}/bin/uvicorn" ]; then
  CMD=("${VENV_DIR}/bin/uvicorn" "${CMD_ARGS[@]}")
elif command -v uvicorn >/dev/null 2>&1; then
  CMD=("$(command -v uvicorn)" "${CMD_ARGS[@]}")
elif command -v python3 >/dev/null 2>&1 && python3 - <<'PY' >/dev/null 2>&1
import uvicorn
PY
then
  CMD=("python3" "-m" "uvicorn" "${CMD_ARGS[@]}")
elif command -v python >/dev/null 2>&1 && python - <<'PY' >/dev/null 2>&1
import uvicorn
PY
then
  CMD=("python" "-m" "uvicorn" "${CMD_ARGS[@]}")
else
  log_err "[server] ✗ uvicorn is not installed in venv (${VENV_DIR}) or system."
  log_err "[server] ✗ Run: bash scripts/steps/03_install_deps.sh"
  exit 127
fi

# Start as a new session so Ctrl+C in the calling shell won't touch it.
# Write the session leader PID so we can kill the whole tree later.
setsid "${CMD[@]}" >> "${ROOT_DIR}/server.log" 2>&1 &
SERVER_PID=$!
echo "${SERVER_PID}" > "${ROOT_DIR}/server.pid"

log_info "[server] Waiting for server to become healthy (timeout ${WARMUP_TIMEOUT_SECS}s)..."

if ! wait_for_server_health; then
  log_err "[server] ✗ Server did not become healthy within ${WARMUP_TIMEOUT_SECS}s"
  log_err "[server] Check logs: tail -f ${ROOT_DIR}/server.log"
  # Kill the unhealthy server process
  if [ -f "${ROOT_DIR}/server.pid" ]; then
    kill -TERM "-$(cat "${ROOT_DIR}/server.pid")" 2>/dev/null || true
    rm -f "${ROOT_DIR}/server.pid"
  fi
  exit 1
fi

log_info "[server] ✓ Server started"
health_hint="${SERVER_HEALTH_URLS[0]:-http://${SERVER_ADDR}/healthz}"
log_info "[server] Health: curl -s ${health_hint}"
log_info "[server] All logs: tail -f ${ROOT_DIR}/server.log"
log_info "[server] Stop: kill -TERM -$(cat "${ROOT_DIR}/server.pid")"
log_blank

WARMUP_SCRIPT="${ROOT_DIR}/scripts/warmup.sh"
if [ -x "${WARMUP_SCRIPT}" ]; then
  log_info "[warmup] Running warmup validation script..."
  if ! "${WARMUP_SCRIPT}"; then
    log_warn "[warmup] ⚠ Warmup script detected issues (see logs/warmup.log)"
  fi
else
  log_warn "[warmup] ⚠ Warmup script not found at ${WARMUP_SCRIPT}"
fi
