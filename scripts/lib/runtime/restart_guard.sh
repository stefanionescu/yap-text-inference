#!/usr/bin/env bash
# =============================================================================
# Restart Guard Utilities
# =============================================================================
# Helpers for detecting running deployments and comparing config snapshots.
# Detects engine switching (vLLM/TRT) that requires full environment wipe.

_RUNTIME_GUARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/runtime/cleanup.sh
source "${_RUNTIME_GUARD_DIR}/cleanup.sh"

_runtime_guard_pid_file() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  printf '%s/server.pid' "${root_dir}"
}

_runtime_guard_last_config_file() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  printf '%s/.run/last_config.env' "${root_dir}"
}

runtime_guard_get_running_server_pid() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  local pid_file
  pid_file="$(_runtime_guard_pid_file "${root_dir}")"

# Treat server.pid as best-effort bookkeeping: only return the PID if the
# process is still alive, otherwise drop the stale file so a fresh launch can
# claim it.
  if [ -f "${pid_file}" ]; then
    local existing_pid
    existing_pid="$(cat "${pid_file}" 2>/dev/null || true)"
    if [ -n "${existing_pid}" ] && ps -p "${existing_pid}" >/dev/null 2>&1; then
      printf '%s' "${existing_pid}"
      return 0
    fi
    log_warn "[server] ⚠ Found stale server.pid entry; removing ${pid_file}"
    rm -f "${pid_file}" || true
  fi
  return 1
}

runtime_guard_read_last_config_value() {
  local key="$1"
  local root_dir="${2:-${ROOT_DIR:-}}"
  local config_file
  config_file="$(_runtime_guard_last_config_file "${root_dir}")"

  if [ -f "${config_file}" ]; then
    local line
    line="$(grep -E "^${key}=" "${config_file}" 2>/dev/null || true)"
    if [ -n "${line}" ]; then
      echo "${line#*=}"
    fi
  fi
}

# Check if engine has changed since last run (requires full wipe)
# Returns: 0 if engine changed, 1 if same or first run
runtime_guard_engine_changed() {
  local desired_engine="${1:-trt}"
  local root_dir="${2:-${ROOT_DIR:-}}"
  
  local last_engine
  last_engine="$(runtime_guard_read_last_config_value "INFERENCE_ENGINE" "${root_dir}")"
  
  # If no previous engine recorded, assume no change needed
  if [ -z "${last_engine:-}" ]; then
    return 1  # No change detected (first run)
  fi
  
  # Normalize both to lowercase for comparison
  desired_engine="$(echo "${desired_engine}" | tr '[:upper:]' '[:lower:]')"
  last_engine="$(echo "${last_engine}" | tr '[:upper:]' '[:lower:]')"
  
  if [ "${desired_engine}" != "${last_engine}" ]; then
    return 0  # Engine changed
  fi
  return 1  # Same engine
}

# Force full environment wipe when switching engines
# Internal function - use runtime_guard_handle_engine_switch instead
_runtime_guard_force_engine_wipe() {
  local script_dir="$1"
  local root_dir="$2"
  local from_engine="$3"
  local to_engine="$4"
  
  log_section "[server] ⚠ Engine switch detected: ${from_engine} → ${to_engine}"
  
  # Force full cleanup (engine switch requires fresh deps)
  if ! FULL_CLEANUP=1 bash "${script_dir}/stop.sh"; then
    log_err "[server] ✗ stop.sh failed during engine wipe"
    return 1
  fi
  
  # Also remove engine-specific directories
  cleanup_engine_artifacts "${root_dir}"
  
  log_info "[server] Engine wipe complete. Ready for fresh ${to_engine} deployment."
  log_blank
}

# =============================================================================
# UNIFIED ENGINE SWITCH HANDLING
# =============================================================================
# Single entry point for handling engine switches across all scripts.
# Call this at the start of main.sh/restart.sh BEFORE any heavy operations.
#
# Usage: runtime_guard_handle_engine_switch <script_dir> <root_dir> <desired_engine>
# Returns: 0 if engine switch was handled (wipe done), 1 if no switch needed,
#          2 if a wipe was attempted but failed
# Sets: ENGINE_SWITCH_HANDLED=1 if wipe was performed
#
runtime_guard_handle_engine_switch() {
  local script_dir="$1"
  local root_dir="$2"
  local desired_engine="${3:-trt}"
  
  # Skip if already handled in this session
  if [ "${ENGINE_SWITCH_HANDLED:-0}" = "1" ]; then
    return 1  # Already handled
  fi
  
  if ! runtime_guard_engine_changed "${desired_engine}" "${root_dir}"; then
    return 1  # No engine switch needed
  fi
  
  local last_engine
  last_engine="$(runtime_guard_read_last_config_value "INFERENCE_ENGINE" "${root_dir}")"
  
  # Normalize for display
  local norm_desired norm_last
  norm_desired="$(echo "${desired_engine}" | tr '[:upper:]' '[:lower:]')"
  norm_last="$(echo "${last_engine}" | tr '[:upper:]' '[:lower:]')"
  
  # Perform the wipe
  if ! _runtime_guard_force_engine_wipe "${script_dir}" "${root_dir}" "${norm_last}" "${norm_desired}"; then
    log_err "[server] ✗ Engine switch wipe failed"
    return 2  # Error
  fi
  
  # Mark as handled so we don't double-wipe
  export ENGINE_SWITCH_HANDLED=1
  return 0  # Switch handled
}

# Compare the requested deployment parameters with the last snapshot.
# Returns 0 when everything matches (safe to keep caches) and 1 otherwise.
runtime_guard_configs_match() {
  local desired_deploy="$1"
  local desired_chat="$2"
  local desired_tool="$3"
  local desired_quant="$4"
  local desired_chat_quant="$5"
  local desired_engine="${6:-trt}"
  local root_dir="${7:-${ROOT_DIR:-}}"

  local last_deploy last_chat last_tool last_quant last_chat_quant last_engine
  last_deploy="$(runtime_guard_read_last_config_value "DEPLOY_MODE" "${root_dir}")"
  last_chat="$(runtime_guard_read_last_config_value "CHAT_MODEL" "${root_dir}")"
  last_tool="$(runtime_guard_read_last_config_value "TOOL_MODEL" "${root_dir}")"
  last_quant="$(runtime_guard_read_last_config_value "QUANTIZATION" "${root_dir}")"
  last_chat_quant="$(runtime_guard_read_last_config_value "CHAT_QUANTIZATION" "${root_dir}")"
  last_engine="$(runtime_guard_read_last_config_value "INFERENCE_ENGINE" "${root_dir}")"

  if [ -z "${last_deploy:-}" ]; then
    return 1
  fi

  # Normalize engines for comparison
  desired_engine="$(echo "${desired_engine:-trt}" | tr '[:upper:]' '[:lower:]')"
  last_engine="$(echo "${last_engine:-}" | tr '[:upper:]' '[:lower:]')"

  if [ "${desired_deploy:-}" = "${last_deploy:-}" ] &&
     [ "${desired_chat:-}" = "${last_chat:-}" ] &&
     [ "${desired_tool:-}" = "${last_tool:-}" ] &&
     [ "${desired_quant:-}" = "${last_quant:-}" ] &&
     [ "${desired_chat_quant:-}" = "${last_chat_quant:-}" ] &&
     [ "${desired_engine:-}" = "${last_engine:-}" ]; then
    return 0
  fi
  return 1
}

# Decide whether to stop a running server and whether caches can be preserved.
# Handles engine switches (which force a wipe) and compares config snapshots
# to decide between a light stop (keep caches) and a full reset.
runtime_guard_stop_server_if_needed() {
  local script_dir="$1"; shift
  local root_dir="$1"; shift
  local desired_deploy="$1"; shift
  local desired_chat="$1"; shift
  local desired_tool="$1"; shift
  local desired_quant="$1"; shift
  local desired_chat_quant="$1"; shift
  local desired_engine="${1:-trt}"

  # Handle engine switching via unified function (skips if already handled)
  local switch_result=0
  runtime_guard_handle_engine_switch "${script_dir}" "${root_dir}" "${desired_engine}" || switch_result=$?
  
  case "${switch_result}" in
    0)
      # Engine switch was handled (wipe done), continue with deployment
      return 0
      ;;
    2)
      # Error during engine switch
      return 1
      ;;
    # 1 = no switch needed, continue below
  esac

  local running_pid
  if ! running_pid="$(runtime_guard_get_running_server_pid "${root_dir}")"; then
    return 0
  fi

  log_blank
  log_warn "[server] ⚠ Server already running (PID=${running_pid}). Evaluating restart strategy..."
  if runtime_guard_configs_match \
       "${desired_deploy}" \
       "${desired_chat}" \
       "${desired_tool}" \
       "${desired_quant}" \
       "${desired_chat_quant}" \
       "${desired_engine}" \
       "${root_dir}"
  then
    log_info "[server] Existing server matches requested config; stopping without clearing caches."
    if ! FULL_CLEANUP=0 bash "${script_dir}/stop.sh"; then
      log_err "[server] ✗ stop.sh failed during light stop"
      return 1
    fi
  else
    log_info "[server] Requested configuration differs; performing full reset before redeploy."
    if ! FULL_CLEANUP=1 bash "${script_dir}/stop.sh"; then
      log_err "[server] ✗ stop.sh failed during full reset"
      return 1
    fi
  fi
}

# Persist the last-known-good deployment config for future comparisons.
runtime_guard_write_snapshot() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  local run_dir="${root_dir}/.run"
  local env_file="${run_dir}/last_config.env"
  mkdir -p "${run_dir}"
  {
    echo "# Autogenerated by runtime_guard_write_snapshot"
    echo "INFERENCE_ENGINE=${INFERENCE_ENGINE:-trt}"
    echo "QUANTIZATION=${QUANTIZATION:-}"
    echo "DEPLOY_MODE=${DEPLOY_MODE:-}"
    echo "CHAT_MODEL=${CHAT_MODEL:-}"
    echo "TOOL_MODEL=${TOOL_MODEL:-}"
    echo "CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-}"
    echo "KV_DTYPE=${KV_DTYPE:-}"
    echo "GPU_SM_ARCH=${GPU_SM_ARCH:-}"
  } > "${env_file}" 2>/dev/null || true
}
