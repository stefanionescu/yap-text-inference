#!/usr/bin/env bash
# =============================================================================
# Restart Launch Helper
# =============================================================================
# Server launch helper for scripts/restart.sh. Handles runtime config
# persistence and delegates to pipeline utilities for background startup.

_RESTART_LAUNCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/core.sh
source "${_RESTART_LAUNCH_DIR}/../../config/values/core.sh"

launch_server_background() {
  if [ "${RESTART_RUNTIME_SNAPSHOT_DIRTY:-0}" = "1" ]; then
    log_info "[restart] Persisting overridden runtime defaults before relaunch (.run/last_config.env)"
    write_snapshot "${ROOT_DIR}"
    RESTART_RUNTIME_SNAPSHOT_DIRTY=0
  fi

  local command_string="bash '${ROOT_DIR}/scripts/steps/05_start_server.sh'"
  local quant_label="${CHAT_QUANTIZATION:-auto}"
  local engine_label="${INFERENCE_ENGINE:-${CFG_DEFAULT_ENGINE}}"
  run_background \
    "${ROOT_DIR}" \
    "${command_string}" \
    "1" \
    "Starting server (${engine_label} engine, ${quant_label} quantization)..."
}
