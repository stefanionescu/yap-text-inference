#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

PID_FILE="${ROOT_DIR}/server.pid"

if [ -f "${PID_FILE}" ]; then
  PID="$(cat "${PID_FILE}")"
  if ps -p "${PID}" >/dev/null 2>&1; then
    log_info "Stopping server PID ${PID}"
    kill -TERM "${PID}" || true
    # optional: wait up to 10s then SIGKILL
    for _ in {1..10}; do
      ps -p "${PID}" >/dev/null 2>&1 || break
      sleep 1
    done
    ps -p "${PID}" >/dev/null 2>&1 && kill -KILL "${PID}" || true
  fi
  rm -f "${PID_FILE}"
else
  log_warn "No PID file; using pattern kill as fallback"
  pkill -f 'uvicorn src.server:app' || true
fi

log_info "Server stopped"


