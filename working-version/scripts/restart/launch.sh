#!/usr/bin/env bash

# Launch helper for scripts/restart.sh

_log_info() { echo "[restart:launch] $*"; }

restart_server_background() {
  _log_info "Starting server using existing engine at '${TRTLLM_ENGINE_DIR:-}'..."
  exec bash "scripts/runtime/start-server.sh"
}
