#!/usr/bin/env bash

# Launch helper for scripts/restart.sh
# Requires: ROOT_DIR

restart_start_server_background() {
  local SERVER_LOG="${ROOT_DIR}/server.log"
  touch "${SERVER_LOG}"
  log_info "Starting server directly with existing AWQ models..."
  log_info "All logs: tail -f server.log"
  log_info "To stop: bash scripts/stop.sh"
  log_info ""
  mkdir -p "${ROOT_DIR}/.run"
  setsid nohup "${ROOT_DIR}/scripts/steps/05_start_server.sh" </dev/null >> "${SERVER_LOG}" 2>&1 &
  local BG_PID=$!
  echo "${BG_PID}" > "${ROOT_DIR}/.run/deployment.pid"
  log_info "Server started (PID: ${BG_PID})"
  log_info "Following logs (Ctrl+C detaches, server continues)..."
  exec tail -n +1 -F "${SERVER_LOG}"
}


