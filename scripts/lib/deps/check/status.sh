#!/usr/bin/env bash
# =============================================================================
# Dependency Check - Runtime Status Aggregation
# =============================================================================
# venv probes and aggregate status helpers used by TRT dependency install flow.

# Minimal venv existence check (no dependency on other helpers)
check_venv_exists() {
  local venv_dir="${1:-${VENV_DIR:-${ROOT_DIR}/.venv}}"

  if [[ ! -d $venv_dir ]]; then
    return 1
  fi
  if [[ ! -f "$venv_dir/bin/python" ]]; then
    return 1
  fi
  if [[ ! -f "$venv_dir/bin/activate" ]]; then
    return 1
  fi
  return 0
}

# Log a human-readable summary of current TRT dep status
log_trt_dep_status() {
  local venv_dir="${1:-${VENV_DIR:-${ROOT_DIR}/.venv}}"
  echo "[deps] Status for venv=${venv_dir}"
  local ok="✓" bad="✗"
  _status_line() {
    local label="$1" need="$2"
    if [[ ${need} == "0" ]]; then
      printf "[deps]   %-14s %s\n" "${label}:" "${ok}"
    else
      printf "[deps]   %-14s %s\n" "${label}:" "${bad}"
    fi
  }
  _status_line "torch" "${NEEDS_PYTORCH}"
  _status_line "torchvision" "${NEEDS_TORCHVISION}"
  _status_line "tensorrt_llm" "${NEEDS_TRTLLM}"
  _status_line "requirements" "${NEEDS_REQUIREMENTS}"
  if [[ -n ${NEEDS_FLASHINFER:-} ]]; then
    _status_line "flashinfer" "${NEEDS_FLASHINFER}"
  fi
}

# Check all TRT Python dependencies in a venv
# Sets NEEDS_PYTORCH, NEEDS_TORCHVISION, NEEDS_TRTLLM, NEEDS_REQUIREMENTS globals
# Returns: 0 if all satisfied, 1 if any missing
check_trt_deps_status() {
  local venv_dir="${1:-${VENV_DIR:-${ROOT_DIR}/.venv}}"
  local pytorch_ver="${2:-${CFG_TRT_PYTORCH_VERSION}}"
  local torchvision_ver="${3:-${CFG_TRT_TORCHVISION_VERSION}}"
  local trtllm_ver="${4:-${CFG_TRT_VERSION}}"
  local req_file="${5:-requirements-trt.txt}"

  NEEDS_PYTORCH=1
  NEEDS_TORCHVISION=1
  NEEDS_TRTLLM=1
  NEEDS_REQUIREMENTS=1
  NEEDS_FLASHINFER=1

  if ! check_venv_exists "${venv_dir}" 2>/dev/null; then
    return 1
  fi

  local venv_py="${venv_dir}/bin/python"

  if check_pytorch_installed "${pytorch_ver}" "${venv_py}"; then
    NEEDS_PYTORCH=0
  fi

  if check_torchvision_installed "${torchvision_ver}" "${venv_py}"; then
    NEEDS_TORCHVISION=0
  fi

  if check_trtllm_installed "${trtllm_ver}" "${venv_py}"; then
    NEEDS_TRTLLM=0
  fi

  if check_requirements_installed "${req_file}" "${venv_py}"; then
    NEEDS_REQUIREMENTS=0
  fi

  if check_flashinfer_installed "${venv_py}"; then
    NEEDS_FLASHINFER=0
  fi

  # Return 0 if all satisfied
  if [[ $NEEDS_PYTORCH == "0" && $NEEDS_TORCHVISION == "0" && $NEEDS_TRTLLM == "0" && $NEEDS_REQUIREMENTS == "0" && $NEEDS_FLASHINFER == "0" ]]; then
    return 0
  fi

  return 1
}
