#!/usr/bin/env bash
# =============================================================================
# Restart Guard - Engine Switch Logic
# =============================================================================
# Engine-change detection and full-wipe handling.

# Check if engine has changed since last run (requires full wipe)
# Returns: 0 if engine changed, 1 if same or first run
engine_changed() {
  local desired_engine="${1:-${CFG_DEFAULT_ENGINE}}"
  local root_dir="${2:-${ROOT_DIR:-}}"

  local last_engine
  last_engine="$(read_last_config_value "INFERENCE_ENGINE" "${root_dir}")"

  # If no previous engine recorded, assume no change needed.
  if [ -z "${last_engine:-}" ]; then
    return 1
  fi

  # Normalize both to lowercase for comparison.
  desired_engine="$(echo "${desired_engine}" | tr '[:upper:]' '[:lower:]')"
  last_engine="$(echo "${last_engine}" | tr '[:upper:]' '[:lower:]')"

  if [ "${desired_engine}" != "${last_engine}" ]; then
    return 0
  fi
  return 1
}

# Force full environment wipe when switching engines
# Internal function - use handle_engine_switch instead.
_force_engine_wipe() {
  local script_dir="$1"
  local root_dir="$2"
  local from_engine="$3"
  local to_engine="$4"
  local suppress_message="${5:-0}"

  if [ "${suppress_message}" != "1" ]; then
    log_section "[server] ⚠ Engine switch detected: ${from_engine} → ${to_engine}"
  fi

  # Force full cleanup (engine switch requires fresh deps).
  if ! FULL_CLEANUP=1 bash "${script_dir}/stop.sh"; then
    log_err "[server] ✗ stop.sh failed during engine wipe"
    return 1
  fi

  # Also remove engine-specific directories.
  cleanup_engine_artifacts "${root_dir}"

  if [ "${suppress_message}" != "1" ]; then
    log_info "[server] Engine wipe complete. Ready for fresh ${to_engine} deployment."
  else
    log_info "[server] Environment wipe complete. Ready for tool-only deployment."
  fi
  log_blank
}

# Unified engine switch handling.
# Usage: handle_engine_switch <script_dir> <root_dir> <desired_engine> [deploy_mode]
# Returns: 0 if engine switch was handled, 1 if no switch needed, 2 on error.
handle_engine_switch() {
  local script_dir="$1"
  local root_dir="$2"
  local desired_engine="${3:-${CFG_DEFAULT_ENGINE}}"
  local deploy_mode="${4:-${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}}"

  # Skip if already handled in this session.
  if [ "${ENGINE_SWITCH_HANDLED:-0}" = "1" ]; then
    return 1
  fi

  # Tool-only mode doesn't use an inference engine.
  if [ "${deploy_mode}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    return 1
  fi

  if ! engine_changed "${desired_engine}" "${root_dir}"; then
    return 1
  fi

  local last_engine
  last_engine="$(read_last_config_value "INFERENCE_ENGINE" "${root_dir}")"

  local norm_desired norm_last
  norm_desired="$(echo "${desired_engine}" | tr '[:upper:]' '[:lower:]')"
  norm_last="$(echo "${last_engine}" | tr '[:upper:]' '[:lower:]')"

  local suppress_message=0
  if [ "${deploy_mode}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    suppress_message=1
  fi

  if ! _force_engine_wipe "${script_dir}" "${root_dir}" "${norm_last}" "${norm_desired}" "${suppress_message}"; then
    log_err "[server] ✗ Engine switch wipe failed"
    return 2
  fi

  export ENGINE_SWITCH_HANDLED=1
  return 0
}
