#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Starting server on :8000 in background"
cd "${ROOT_DIR}"
if [ -d "${ROOT_DIR}/.venv" ]; then
  source "${ROOT_DIR}/.venv/bin/activate"
fi

# Start as a new session so Ctrl+C in the calling shell won't touch it.
# Write the session leader PID so we can kill the whole tree later.
setsid uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1 > "${ROOT_DIR}/server.log" 2>&1 &
SERVER_PID=$!
echo "${SERVER_PID}" > "${ROOT_DIR}/server.pid"

sleep 1
if ps -p "$(cat "${ROOT_DIR}/server.pid" 2>/dev/null)" >/dev/null 2>&1; then
  log_info "Server started: PID=$(cat "${ROOT_DIR}/server.pid")"
  log_info "Health:  curl -s http://127.0.0.1:8000/healthz"
  log_info "Logs:    tail -f ${ROOT_DIR}/server.log"
  log_info "Stop:    kill -TERM -$(cat ${ROOT_DIR}/server.pid)  # negative PID kills session"
else
  log_warn "Server may have failed to start. See ${ROOT_DIR}/server.log"
  exit 1
fi

