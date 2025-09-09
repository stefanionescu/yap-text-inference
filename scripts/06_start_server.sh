#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Starting server on :8080 in background"
cd "${ROOT_DIR}"
if [ -d "${ROOT_DIR}/.venv" ]; then
  source "${ROOT_DIR}/.venv/bin/activate"
fi

# Start server in background, redirect output to log file
nohup uvicorn src.server:app --host 0.0.0.0 --port 8080 --workers 1 > server.log 2>&1 &
SERVER_PID=$!

log_info "Server started with PID ${SERVER_PID}"
log_info "Logs: tail -f ${ROOT_DIR}/server.log"
log_info "Stop: pkill -f 'uvicorn src.server:app' or bash scripts/stop.sh"


