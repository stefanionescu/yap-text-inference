#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Pre-Built Engine Detection from HuggingFace
# =============================================================================
# Utilities for discovering and downloading pre-built TensorRT-LLM engines
# from HuggingFace repositories. Engines are GPU-specific and require exact
# SM arch, TRT-LLM version, and CUDA version matching.

_TRT_ENGINE_HF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_TRT_ENGINE_HF_ROOT="${ROOT_DIR:-$(cd "${_TRT_ENGINE_HF_DIR}/../../.." && pwd)}"

# =============================================================================
# ENGINE LABEL PARSING
# =============================================================================

# Parse engine label into components
# Usage: parse_engine_label <label>
# Returns: sm_arch trtllm_version cuda_version (space-separated)
# Example: "sm90_trt-llm-1.2.0rc5_cuda13.0" -> "sm90 1.2.0rc5 13.0"
parse_engine_label() {
  local label="${1:-}"
  if [ -z "${label}" ]; then
    return 1
  fi
  
  # Format: sm{arch}_trt-llm-{version}_cuda{version}
  local sm_arch trtllm_version cuda_version
  
  # Extract SM arch (first part before _trt-llm-)
  sm_arch="${label%%_trt-llm-*}"
  
  # Extract TRT-LLM version (between _trt-llm- and _cuda)
  local rest="${label#*_trt-llm-}"
  trtllm_version="${rest%%_cuda*}"
  
  # Extract CUDA version (after _cuda)
  cuda_version="${rest#*_cuda}"
  
  if [ -z "${sm_arch}" ] || [ -z "${trtllm_version}" ] || [ -z "${cuda_version}" ]; then
    return 1
  fi
  
  echo "${sm_arch} ${trtllm_version} ${cuda_version}"
}

# =============================================================================
# REMOTE ENGINE LISTING
# =============================================================================

# List available engine directories from a HuggingFace TRT repo
# Returns newline-separated list of engine labels (e.g., "sm90_trt-llm-1.2.0rc5_cuda13.0")
# Usage: list_remote_engines <repo_id>
list_remote_engines() {
  local repo_id="${1:-}"
  if [ -z "${repo_id}" ]; then
    return 1
  fi

  local python_root="${ROOT_DIR:-${_TRT_ENGINE_HF_ROOT}}"
  PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
    python -m src.scripts.trt.detection list-engines "${repo_id}" 2>/dev/null || true
}

# =============================================================================
# COMPATIBILITY MATCHING
# =============================================================================

# Check if a remote engine label matches current system
# Usage: engine_matches_system <label>
# Returns: 0 if compatible, 1 if not
engine_matches_system() {
  local label="${1:-}"
  if [ -z "${label}" ]; then
    return 1
  fi
  
  local current_sm="${GPU_SM_ARCH:-$(detect_sm_arch)}"
  local current_trtllm
  current_trtllm=$(detect_trtllm_version)
  local current_cuda
  current_cuda=$(detect_cuda_version)
  
  # Parse the remote engine label
  local parsed
  parsed=$(parse_engine_label "${label}") || return 1
  read -r remote_sm remote_trtllm remote_cuda <<< "${parsed}"
  
  # Check SM arch match (must be exact - engines are GPU-specific)
  if [ "${remote_sm}" != "${current_sm}" ]; then
    return 1
  fi
  
  # Check TRT-LLM version match (exact match required for ABI compatibility)
  if [ "${remote_trtllm}" != "${current_trtllm}" ]; then
    return 1
  fi
  
  # Check CUDA version match (major.minor must match)
  # Allow for minor differences in patch version (e.g., 13.0 ~= 13.0.1)
  local remote_cuda_major_minor="${remote_cuda%.*}"
  local current_cuda_major_minor="${current_cuda%.*}"
  
  # Handle case where CUDA is just major.minor (no patch)
  if [[ "${remote_cuda}" != *.*.* ]]; then
    remote_cuda_major_minor="${remote_cuda}"
  fi
  if [[ "${current_cuda}" != *.*.* ]]; then
    current_cuda_major_minor="${current_cuda}"
  fi
  
  if [ "${remote_cuda_major_minor}" != "${current_cuda_major_minor}" ]; then
    return 1
  fi
  
  return 0
}

# Find a compatible pre-built engine from a HuggingFace repo
# Usage: find_compatible_engine <repo_id>
# Returns: engine label if found, empty string if none compatible
find_compatible_engine() {
  local repo_id="${1:-}"
  if [ -z "${repo_id}" ]; then
    return 1
  fi
  
  local current_sm="${GPU_SM_ARCH:-$(detect_sm_arch)}"
  local current_trtllm
  current_trtllm=$(detect_trtllm_version)
  local current_cuda
  current_cuda=$(detect_cuda_version)
  
  log_info "[engine] Checking for pre-built engines for this GPU..."

  local engines
  engines=$(list_remote_engines "${repo_id}")
  
  if [ -z "${engines}" ]; then
    log_info "[engine]   No pre-built engines found in repository"
    return 1
  fi
  
  local engine
  while IFS= read -r engine; do
    if [ -z "${engine}" ]; then
      continue
    fi
    if engine_matches_system "${engine}"; then
      log_info "[engine] ✓ Found compatible engine for GPU"
      echo "${engine}"
      return 0
    fi
  done <<< "${engines}"
  
  log_info "[engine] No compatible pre-built engine found"
  return 1
}

# =============================================================================
# ENGINE DOWNLOAD
# =============================================================================

# Download a pre-built engine from HuggingFace
# Usage: download_prebuilt_engine <repo_id> <engine_label> [target_dir]
# Returns: path to downloaded engine directory
download_prebuilt_engine() {
  local repo_id="${1:-}"
  local engine_label="${2:-}"
  local target_dir="${3:-}"
  
  if [ -z "${repo_id}" ] || [ -z "${engine_label}" ]; then
    log_err "[engine] ✗ Repository ID and engine label are required"
    return 1
  fi
  
  if [ -z "${target_dir}" ]; then
    local model_name
    model_name=$(basename "${repo_id}")
    target_dir="${TRT_MODELS_DIR:-${ROOT_DIR:-.}/models}/${model_name}-trt-engine"
  fi
  
  log_info "[engine] Downloading pre-built engine..."
  
  hf_enable_transfer "[engine]" "python" || true
  
  mkdir -p "${target_dir}"
  
  local python_root="${ROOT_DIR:-${_TRT_ENGINE_HF_ROOT}}"
  local engine_dir
  engine_dir=$(PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
    python -m src.scripts.trt.detection download-engine \
    "${repo_id}" "${engine_label}" "${target_dir}" 2>&1) || {
    log_err "[engine] ✗ Failed to download pre-built engine"
    return 1
  }
  
  if [ -n "${engine_dir}" ] && [ -d "${engine_dir}" ]; then
    echo "${engine_dir}"
    return 0
  else
    log_err "[engine] ✗ Downloaded engine directory is invalid or missing engine files"
    return 1
  fi
}

