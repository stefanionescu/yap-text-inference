#!/usr/bin/env bash

# Launch helper for scripts/restart.sh
# Requires: ROOT_DIR

restart_start_server_background() {
  local command_string="bash '${SCRIPT_DIR}/steps/05_start_server.sh'"
  runtime_pipeline_run_background \
    "${ROOT_DIR}" \
    "${command_string}" \
    "1" \
    "Starting server directly with existing AWQ models..."
}


