#!/usr/bin/env bash

# Launch helper for scripts/restart.sh
# Requires: ROOT_DIR

restart_server_background() {
  if [ "${RESTART_RUNTIME_SNAPSHOT_DIRTY:-0}" = "1" ]; then
    log_info "Persisting overridden runtime defaults before relaunch (.run/last_config.env)"
    runtime_guard_write_snapshot "${ROOT_DIR}"
    RESTART_RUNTIME_SNAPSHOT_DIRTY=0
  fi

  local command_string="bash '${ROOT_DIR}/scripts/steps/05_start_server.sh'"
  local quant_label="${QUANTIZATION:-fp8}"
  runtime_pipeline_run_background \
    "${ROOT_DIR}" \
    "${command_string}" \
    "1" \
    "Starting server with ${quant_label} quantization..."
}


