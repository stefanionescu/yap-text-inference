#!/usr/bin/env bash

# Launch helper for scripts/restart.sh
# Requires: ROOT_DIR

restart_start_server_background() {
  local command_string="bash '${ROOT_DIR}/scripts/steps/05_start_server.sh'"
  local quant_label="${QUANTIZATION:-fp8}"
  runtime_pipeline_run_background \
    "${ROOT_DIR}" \
    "${command_string}" \
    "1" \
    "Starting server with ${quant_label} quantization..."
}


