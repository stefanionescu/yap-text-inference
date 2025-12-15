#!/usr/bin/env bash

# Shared helpers for detecting running deployments and comparing config snapshots.
# Tracks engine type (vllm/trt) to detect engine switching that requires full wipe.

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

  if [ -f "${pid_file}" ]; then
    local existing_pid
    existing_pid="$(cat "${pid_file}" 2>/dev/null || true)"
    if [ -n "${existing_pid}" ] && ps -p "${existing_pid}" >/dev/null 2>&1; then
      printf '%s' "${existing_pid}"
      return 0
    fi
    log_warn "Found stale server.pid entry; removing ${pid_file}"
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
runtime_guard_force_engine_wipe() {
  local script_dir="$1"
  local root_dir="$2"
  local from_engine="$3"
  local to_engine="$4"
  
  log_warn "=========================================="
  log_warn "ENGINE SWITCH DETECTED: ${from_engine} → ${to_engine}"
  log_warn "=========================================="
  log_warn "This requires a FULL environment wipe:"
  log_warn "  - All HF caches"
  log_warn "  - All pip dependencies"
  log_warn "  - All quantized model caches"
  log_warn "  - All engine-specific artifacts"
  log_warn "=========================================="
  
  # Force full nuke
  NUKE_ALL=1 bash "${script_dir}/stop.sh"
  
  # Also remove engine-specific directories
  local engine_dirs=(
    "${root_dir}/.venv"
    "${root_dir}/.venv-trt"
    "${root_dir}/.venv-vllm"
    "${root_dir}/.awq"
    "${root_dir}/.trtllm-repo"
    "${root_dir}/models"
  )
  for d in "${engine_dirs[@]}"; do
    if [ -d "$d" ]; then
      log_info "Removing engine artifact: $d"
      rm -rf "$d" || true
    fi
  done
  
  log_info "Engine wipe complete. Ready for fresh ${to_engine} deployment."
}

runtime_guard_configs_match() {
  local desired_deploy="$1"
  local desired_chat="$2"
  local desired_tool="$3"
  local desired_quant="$4"
  local desired_chat_quant="$5"
  local desired_engine="${6:-trt}"
  local root_dir="${7:-${ROOT_DIR:-}}"

  local last_deploy last_chat last_tool last_quant last_chat_quant last_engine
  last_deploy="$(runtime_guard_read_last_config_value "DEPLOY_MODELS" "${root_dir}")"
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

runtime_guard_stop_server_if_needed() {
  local script_dir="$1"; shift
  local root_dir="$1"; shift
  local desired_deploy="$1"; shift
  local desired_chat="$1"; shift
  local desired_tool="$1"; shift
  local desired_quant="$1"; shift
  local desired_chat_quant="$1"; shift
  local desired_engine="${1:-trt}"

  # First check for engine switching - this requires FULL wipe
  local last_engine
  last_engine="$(runtime_guard_read_last_config_value "INFERENCE_ENGINE" "${root_dir}")"
  
  if [ -n "${last_engine:-}" ]; then
    local norm_desired norm_last
    norm_desired="$(echo "${desired_engine}" | tr '[:upper:]' '[:lower:]')"
    norm_last="$(echo "${last_engine}" | tr '[:upper:]' '[:lower:]')"
    
    if [ "${norm_desired}" != "${norm_last}" ]; then
      log_warn "Engine switch detected: ${norm_last} → ${norm_desired}"
      runtime_guard_force_engine_wipe "${script_dir}" "${root_dir}" "${norm_last}" "${norm_desired}"
      return 0
    fi
  fi

  local running_pid
  if ! running_pid="$(runtime_guard_get_running_server_pid "${root_dir}")"; then
    return 0
  fi

  log_warn "Server already running (PID=${running_pid}). Evaluating restart strategy..."
  if runtime_guard_configs_match \
       "${desired_deploy}" \
       "${desired_chat}" \
       "${desired_tool}" \
       "${desired_quant}" \
       "${desired_chat_quant}" \
       "${desired_engine}" \
       "${root_dir}"
  then
    log_info "Existing server matches requested config; stopping without clearing caches."
    NUKE_ALL=0 bash "${script_dir}/stop.sh"
  else
    log_info "Requested configuration differs; performing full reset before redeploy."
    NUKE_ALL=1 bash "${script_dir}/stop.sh"
  fi
}

runtime_guard_write_snapshot() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  local run_dir="${root_dir}/.run"
  local env_file="${run_dir}/last_config.env"
  mkdir -p "${run_dir}"
  {
    echo "# Autogenerated by runtime_guard_write_snapshot"
    echo "INFERENCE_ENGINE=${INFERENCE_ENGINE:-trt}"
    echo "QUANTIZATION=${QUANTIZATION:-}"
    echo "DEPLOY_MODELS=${DEPLOY_MODELS:-}"
    echo "CHAT_MODEL=${CHAT_MODEL:-}"
    echo "TOOL_MODEL=${TOOL_MODEL:-}"
    echo "CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-}"
    echo "KV_DTYPE=${KV_DTYPE:-}"
    echo "GPU_SM_ARCH=${GPU_SM_ARCH:-}"
  } > "${env_file}" 2>/dev/null || true
}


