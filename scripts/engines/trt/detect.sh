#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Detection Utilities - Entry Point
# =============================================================================
# Centralized entry point for TRT-LLM detection utilities. Sources specialized
# modules for CUDA validation, HuggingFace engine discovery, and version detection.
#
# GPU detection: use lib/common/gpu_detect.sh functions directly.
# CUDA validation: see cuda.sh
# Pre-built engines: see engine_hf.sh

_TRT_DETECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_TRT_DETECT_ROOT="${ROOT_DIR:-$(cd "${_TRT_DETECT_DIR}/../../.." && pwd)}"

# Source common utilities
# shellcheck source=../../lib/common/gpu_detect.sh
source "${_TRT_DETECT_DIR}/../../lib/common/gpu_detect.sh"
# shellcheck source=../../lib/common/hf.sh
source "${_TRT_DETECT_DIR}/../../lib/common/hf.sh"

# Source specialized TRT modules
# shellcheck source=cuda.sh
source "${_TRT_DETECT_DIR}/cuda.sh"
# shellcheck source=engine_hf.sh
source "${_TRT_DETECT_DIR}/engine_hf.sh"

# Export ROOT_DIR for child modules
_TRT_CUDA_ROOT="${_TRT_DETECT_ROOT}"
export _TRT_CUDA_ROOT

# =============================================================================
# TRT-LLM VERSION DETECTION
# =============================================================================

# Detect installed TensorRT-LLM version
# Priority:
#   1. TRTLLM_INSTALLED_VERSION env var (if already detected/cached)
#   2. Python runtime detection (imports tensorrt_llm)
#   3. TRT_VERSION env var (fallback to target version from trt.sh)
# Returns version string (e.g., "1.2.0rc5") or "unknown"
trt_detect_trtllm_version() {
  # 1. Return cached value if already detected
  if [ -n "${TRTLLM_INSTALLED_VERSION:-}" ]; then
    echo "${TRTLLM_INSTALLED_VERSION}"
    return 0
  fi
  
  # 2. Detect via Python import
  if command -v python >/dev/null 2>&1; then
    local version
    version=$(python -c "import tensorrt_llm; print(tensorrt_llm.__version__)" 2>/dev/null | tail -n1 || echo "")
    if [ -n "${version}" ]; then
      # Cache for subsequent calls
      export TRTLLM_INSTALLED_VERSION="${version}"
      echo "${version}"
      return 0
    fi
  fi
  
  # 3. Fall back to target version from trt.sh config
  # This is the version we're installing, should match after successful install
  if [ -n "${TRT_VERSION:-}" ]; then
    echo "${TRT_VERSION}"
    return 0
  fi
  
  echo "unknown"
  return 1
}

# Generate current system's engine label
# Format: sm{arch}_trt-llm-{version}_cuda{version}
# Example: sm90_trt-llm-1.2.0rc5_cuda13.0
trt_get_current_engine_label() {
  local sm_arch="${GPU_SM_ARCH:-$(gpu_detect_sm_arch)}"
  local trtllm_ver
  trtllm_ver=$(trt_detect_trtllm_version)
  local cuda_ver
  cuda_ver=$(trt_detect_cuda_version)
  
  if [ -z "${sm_arch}" ] || [ "${trtllm_ver}" = "unknown" ] || [ -z "${cuda_ver}" ]; then
    echo ""
    return 1
  fi
  
  echo "${sm_arch}_trt-llm-${trtllm_ver}_cuda${cuda_ver}"
}

# =============================================================================
# QUANTIZATION SCRIPT
# =============================================================================

# Get the quantization script for a model
# Uses the standard quantize.py for all models (including MoE)
trt_get_quantize_script() {
  local trtllm_repo="${1:-${TRT_REPO_DIR}}"
  
  echo "${trtllm_repo}/examples/quantization/quantize.py"
}
