#!/usr/bin/env bash
# =============================================================================
# Unified GPU Detection Utilities
# =============================================================================
# Single source of truth for GPU architecture detection across all scripts.
# Used by both TRT-LLM and vLLM engines, and Docker images.
#
# Priority order for detection:
#   1. GPU_SM_ARCH env var (if already set)
#   2. nvidia-smi compute_cap (most reliable)
#   3. Name-based mapping (fallback for older drivers)

# Detect GPU SM architecture
# Returns: sm80 (A100), sm89 (L40S), sm90 (H100), etc.
# Usage: detect_sm_arch
detect_sm_arch() {
  # Return cached value if already set
  if [ -n "${GPU_SM_ARCH:-}" ]; then
    echo "${GPU_SM_ARCH}"
    return 0
  fi

  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo ""
    return 1
  fi

  local sm_arch=""

  # Method 1: Use compute_cap directly (most reliable)
  local compute_cap
  compute_cap=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n1 | tr -d '.' || true)
  if [ -n "${compute_cap}" ] && [[ "${compute_cap}" =~ ^[0-9]+$ ]]; then
    sm_arch="sm${compute_cap}"
    echo "${sm_arch}"
    return 0
  fi

  # Method 2: Fall back to name-based mapping
  local gpu_name
  gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 | tr '[:upper:]' '[:lower:]' || true)

  if [ -z "${gpu_name}" ]; then
    echo ""
    return 1
  fi

  case "${gpu_name}" in
    *"h100"*|*"h200"*)
      sm_arch="sm90"
      ;;
    *"l40s"*|*"l40"*|*"rtx 4090"*|*"rtx 4080"*|*"rtx 4070"*|*"ada"*)
      sm_arch="sm89"
      ;;
    *"a100"*|*"a10"*|*"a30"*|*"rtx 3090"*|*"rtx 3080"*|*"ampere"*)
      sm_arch="sm80"
      ;;
    *"v100"*|*"volta"*)
      sm_arch="sm70"
      ;;
    *)
      # Default to sm89 (L40S) for unknown GPUs - safe for modern deployments
      sm_arch="sm89"
      ;;
  esac

  echo "${sm_arch}"
}

# Get human-readable GPU name
# Usage: get_gpu_name
get_gpu_name() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "Unknown"
    return
  fi
  nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 || echo "Unknown"
}

# Get GPU VRAM in GB
# Usage: detect_vram_gb
detect_vram_gb() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "0"
    return
  fi
  local vram_mb
  vram_mb=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -n1 || true)
  if [ -n "${vram_mb}" ]; then
    echo $((vram_mb / 1024))
  else
    echo "0"
  fi
}

# Get TORCH_CUDA_ARCH_LIST value based on GPU
# Usage: detect_torch_arch_list
detect_torch_arch_list() {
  local gpu_name
  gpu_name=$(get_gpu_name)
  
  case "${gpu_name}" in
    *H100*|*H200*)
      echo "9.0+PTX"
      ;;
    *L40S*|*L40*|*RTX\ 4090*|*RTX\ 4080*)
      echo "8.9+PTX"
      ;;
    *A100*|*A10*|*A30*|*RTX\ 3090*|*RTX\ 3080*)
      echo "8.0+PTX"
      ;;
    *)
      echo "8.0+PTX"
      ;;
  esac
}

# Map SM arch to CUDAARCHS numeric string (e.g., sm90 -> 90)
detect_cudaarchs() {
  local sm="${1:-${GPU_SM_ARCH:-}}"
  if [ -z "${sm}" ]; then
    sm=$(detect_sm_arch)
  fi
  case "${sm}" in
    sm90) echo "90" ;;
    sm89) echo "89" ;;
    sm80) echo "80" ;;
    sm70) echo "70" ;;
    sm75) echo "75" ;;
    *)    echo "" ;;
  esac
}

# Map SM arch to TORCH_CUDA_ARCH_LIST value (e.g., sm89 -> 8.9+PTX)
gpu_sm_to_torch_arch_list() {
  local sm="${1:-}"
  case "${sm}" in
    sm90) echo "9.0+PTX" ;;
    sm89) echo "8.9+PTX" ;;
    sm80) echo "8.0+PTX" ;;
    sm75) echo "7.5+PTX" ;;
    sm70) echo "7.0+PTX" ;;
    *)    echo "" ;;
  esac
}

# Check if GPU supports native FP8 (Hopper, Ada Lovelace)
# Usage: gpu_supports_fp8
gpu_supports_fp8() {
  local sm_arch="${1:-}"
  if [ -z "${sm_arch}" ]; then
    sm_arch=$(detect_sm_arch)
  fi
  
  case "${sm_arch}" in
    sm89|sm90)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

# Initialize GPU detection and export variables
# Usage: gpu_init_detection [log_prefix]
gpu_init_detection() {
  if [ -z "${GPU_SM_ARCH:-}" ]; then
    GPU_SM_ARCH=$(detect_sm_arch)
    export GPU_SM_ARCH
  fi
  
  if [ -z "${DETECTED_GPU_NAME:-}" ]; then
    DETECTED_GPU_NAME=$(get_gpu_name)
    export DETECTED_GPU_NAME
  fi
  
}

# Set GPU-specific environment defaults
# Usage: gpu_apply_env_defaults
gpu_apply_env_defaults() {
  local gpu_name="${DETECTED_GPU_NAME:-$(get_gpu_name)}"
  local sm_arch="${GPU_SM_ARCH:-}"
  
  # Reuse detected SM arch if available; fall back to detection
  if [ -z "${sm_arch}" ]; then
    sm_arch=$(detect_sm_arch)
    if [ -n "${sm_arch}" ]; then
      GPU_SM_ARCH="${sm_arch}"
      export GPU_SM_ARCH
    fi
  fi
  
  # Set TORCH_CUDA_ARCH_LIST if not already set
  if [ -z "${TORCH_CUDA_ARCH_LIST:-}" ]; then
    local torch_arch_list=""
    # Prefer exact SM-based mapping to avoid name mismatches
    torch_arch_list=$(gpu_sm_to_torch_arch_list "${sm_arch}")
    if [ -z "${torch_arch_list}" ]; then
      torch_arch_list="$(detect_torch_arch_list)"
    fi
    export TORCH_CUDA_ARCH_LIST="${torch_arch_list}"
  fi

  # Set CUDAARCHS to match SM arch (needed for building extensions, e.g., modelopt)
  if [ -z "${CUDAARCHS:-}" ]; then
    local cudaarchs
    cudaarchs="$(detect_cudaarchs "${sm_arch}")"
    export CUDAARCHS="${cudaarchs}"
  fi
  
  # Set memory allocation config for modern GPUs
  case "${gpu_name}" in
    *H100*|*H200*|*L40S*|*L40*|*A100*)
      export PYTORCH_ALLOC_CONF="${PYTORCH_ALLOC_CONF:-expandable_segments:True}"
      ;;
  esac
  
  # A100-specific optimizations
  case "${gpu_name}" in
    *A100*)
      export CUDA_DEVICE_MAX_CONNECTIONS="${CUDA_DEVICE_MAX_CONNECTIONS:-1}"
      ;;
  esac
}

