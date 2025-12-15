#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Environment Configuration
# =============================================================================
# Centralized environment variables for TensorRT-LLM deployments.
# Target GPU: L40S (sm89) by default, with support for A100 (sm80) and H100 (sm90).

# =============================================================================
# TRT-LLM VERSION AND INSTALLATION
# =============================================================================

# TensorRT-LLM version (default: 1.2.0rc5 requires CUDA 13.0 and torch 2.9.x)
TRT_VERSION="${TRT_VERSION:-1.2.0rc5}"
TRT_PIP_SPEC="${TRT_PIP_SPEC:-tensorrt_llm==${TRT_VERSION}}"
TRT_EXTRA_INDEX_URL="${TRT_EXTRA_INDEX_URL:-https://pypi.nvidia.com}"

# PyTorch version matching TRT-LLM requirements
TRT_PYTORCH_VERSION="${TRT_PYTORCH_VERSION:-2.9.1+cu130}"
TRT_PYTORCH_INDEX_URL="${TRT_PYTORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}"

# TensorRT-LLM repository for quantization scripts
TRT_REPO_URL="${TRTLLM_REPO_URL:-https://github.com/NVIDIA/TensorRT-LLM.git}"
TRT_REPO_BRANCH="${TRTLLM_REPO_BRANCH:-main}"
TRT_REPO_DIR="${TRTLLM_REPO_DIR:-${ROOT_DIR:-.}/.trtllm-repo}"

# =============================================================================
# GPU ARCHITECTURE
# =============================================================================

# GPU SM architecture (auto-detected if empty)
# L40S = sm89, A100 = sm80, H100 = sm90
GPU_SM_ARCH="${GPU_SM_ARCH:-}"

# GPUs that support native FP8 (Hopper, Ada Lovelace)
TRT_FP8_SM_ARCHS="sm89 sm90"

# =============================================================================
# ENGINE BUILD PARAMETERS
# =============================================================================

# Default build parameters optimized for L40S chat workloads
TRT_MAX_BATCH_SIZE="${TRT_MAX_BATCH_SIZE:-16}"
TRT_MAX_INPUT_LEN="${TRT_MAX_INPUT_LEN:-8192}"
TRT_MAX_OUTPUT_LEN="${TRT_MAX_OUTPUT_LEN:-4096}"
TRT_DTYPE="${TRT_DTYPE:-float16}"

# KV cache memory management
TRT_KV_FREE_GPU_FRAC="${TRT_KV_FREE_GPU_FRAC:-0.92}"
TRT_KV_ENABLE_BLOCK_REUSE="${TRT_KV_ENABLE_BLOCK_REUSE:-0}"

# =============================================================================
# QUANTIZATION PARAMETERS
# =============================================================================

# AWQ quantization defaults (128 block size optimal for quality)
TRT_AWQ_BLOCK_SIZE="${TRT_AWQ_BLOCK_SIZE:-128}"
TRT_CALIB_SIZE="${TRT_CALIB_SIZE:-256}"
TRT_CALIB_BATCH_SIZE="${TRT_CALIB_BATCH_SIZE:-16}"

# =============================================================================
# DIRECTORY PATHS
# =============================================================================

# Model and engine directories (will be set based on model during runtime)
TRT_CHECKPOINT_DIR="${TRT_CHECKPOINT_DIR:-}"
TRT_ENGINE_DIR="${TRTLLM_ENGINE_DIR:-}"

# Cache directories
TRT_CACHE_DIR="${TRT_CACHE_DIR:-${ROOT_DIR:-.}/.trt_cache}"
TRT_MODELS_DIR="${TRT_MODELS_DIR:-${ROOT_DIR:-.}/models}"

# =============================================================================
# HUGGING FACE SETTINGS
# =============================================================================

# Push settings for quantized models
TRT_HF_PUSH_ENABLED="${TRT_HF_PUSH_ENABLED:-0}"
TRT_HF_PUSH_REPO_ID="${TRT_HF_PUSH_REPO_ID:-}"
TRT_HF_PUSH_PRIVATE="${TRT_HF_PUSH_PRIVATE:-1}"
TRT_HF_PUSH_WHAT="${TRT_HF_PUSH_WHAT:-both}"  # checkpoints, engines, or both

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Check if GPU SM arch supports native FP8
trt_gpu_supports_fp8() {
  local sm_arch="${1:-${GPU_SM_ARCH:-}}"
  if [ -z "${sm_arch}" ]; then
    return 1
  fi
  local arch
  for arch in ${TRT_FP8_SM_ARCHS}; do
    if [ "${sm_arch}" = "${arch}" ]; then
      return 0
    fi
  done
  return 1
}

# Map 4bit/8bit to TRT qformat based on GPU architecture
trt_resolve_qformat() {
  local quant_mode="${1:-4bit}"
  local sm_arch="${2:-${GPU_SM_ARCH:-}}"
  
  case "${quant_mode}" in
    4bit|awq|int4_awq)
      echo "int4_awq"
      ;;
    8bit)
      if trt_gpu_supports_fp8 "${sm_arch}"; then
        echo "fp8"
      else
        echo "int8_sq"
      fi
      ;;
    fp8)
      echo "fp8"
      ;;
    int8|int8_sq)
      echo "int8_sq"
      ;;
    *)
      echo "int4_awq"
      ;;
  esac
}

# Get KV cache dtype based on qformat
trt_resolve_kv_cache_dtype() {
  local qformat="${1:-int4_awq}"
  
  case "${qformat}" in
    int4_awq)
      echo "int8"
      ;;
    fp8)
      echo "fp8"
      ;;
    int8_sq)
      echo "int8"
      ;;
    *)
      echo "int8"
      ;;
  esac
}

# Export all TRT environment variables
trt_export_env() {
  export TRT_VERSION TRT_PIP_SPEC TRT_EXTRA_INDEX_URL
  export TRT_PYTORCH_VERSION TRT_PYTORCH_INDEX_URL
  export TRT_REPO_URL TRT_REPO_BRANCH TRT_REPO_DIR
  export GPU_SM_ARCH TRT_FP8_SM_ARCHS
  export TRT_MAX_BATCH_SIZE TRT_MAX_INPUT_LEN TRT_MAX_OUTPUT_LEN TRT_DTYPE
  export TRT_KV_FREE_GPU_FRAC TRT_KV_ENABLE_BLOCK_REUSE
  export TRT_AWQ_BLOCK_SIZE TRT_CALIB_SIZE TRT_CALIB_BATCH_SIZE
  export TRT_CHECKPOINT_DIR TRT_ENGINE_DIR TRT_CACHE_DIR TRT_MODELS_DIR
  export TRT_HF_PUSH_ENABLED TRT_HF_PUSH_REPO_ID TRT_HF_PUSH_PRIVATE TRT_HF_PUSH_WHAT
}

