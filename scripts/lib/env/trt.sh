#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Environment Configuration
# =============================================================================
# Derives TRT parameters from existing config (limits.py, env.py).
# Does NOT define new defaults - reuses MAX_CONCURRENT_CONNECTIONS, CHAT_MAX_LEN, etc.

# =============================================================================
# TRT-LLM VERSION AND INSTALLATION
# =============================================================================

TRT_VERSION="${TRT_VERSION:-1.2.0rc6}"
TRT_PIP_SPEC="${TRT_PIP_SPEC:-tensorrt_llm==${TRT_VERSION}}"
TRT_EXTRA_INDEX_URL="${TRT_EXTRA_INDEX_URL:-https://pypi.nvidia.com}"

# PyTorch version matching TRT-LLM requirements
# TensorRT-LLM 1.2.0rc6 requires torch<=2.9.0
TRT_PYTORCH_VERSION="${TRT_PYTORCH_VERSION:-2.9.0+cu130}"
TRT_TORCHVISION_VERSION="${TRT_TORCHVISION_VERSION:-0.24.0+cu130}"
TRT_TORCHAUDIO_VERSION="${TRT_TORCHAUDIO_VERSION:-2.9.0+cu130}"
TRT_PYTORCH_INDEX_URL="${TRT_PYTORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}"

# MPI runtime pin for TRT-LLM (runtime-only, prevents CUDA downgrade)
MPI_VERSION_PIN="${MPI_VERSION_PIN:-4.1.6-7ubuntu2}"

# MPI is required for TRT-LLM multi-GPU inference and quantization workflows
NEED_MPI="${NEED_MPI:-1}"

# TensorRT-LLM repository for quantization scripts
# IMPORTANT: We always clone a specific tag matching TRT_VERSION, not main branch.
# The tag contains the correct quantization/requirements.txt for that version.
TRT_REPO_URL="${TRTLLM_REPO_URL:-https://github.com/Yap-With-AI/TensorRT-LLM.git}"
TRT_REPO_TAG="${TRTLLM_REPO_TAG:-v${TRT_VERSION}}"
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
# ENGINE BUILD PARAMETERS (derived from existing config)
# =============================================================================

# Batch size for TRT engine build - MUST be explicitly set
# This is baked into the compiled engine and cannot be changed at runtime.
# Do NOT derive from MAX_CONCURRENT_CONNECTIONS - these are different concepts.
# TRT_MAX_BATCH_SIZE: max sequences batched in a single forward pass
# MAX_CONCURRENT_CONNECTIONS: max WebSocket connections (users)
#
# Validation is done in trt_quantizer.sh before engine build.
# At this point we just read the value; it may be empty if not building an engine.
TRT_MAX_BATCH_SIZE="${TRT_MAX_BATCH_SIZE:-}"

# Input length = CHAT_MAX_LEN (default 5525 from limits.py)
# This is the total context window: persona + history + user input
if [ -z "${TRT_MAX_INPUT_LEN:-}" ]; then
  TRT_MAX_INPUT_LEN="${CHAT_MAX_LEN:-5525}"
fi

# Output length = CHAT_MAX_OUT (default 150 from limits.py)
if [ -z "${TRT_MAX_OUTPUT_LEN:-}" ]; then
  TRT_MAX_OUTPUT_LEN="${CHAT_MAX_OUT:-150}"
fi

# Data type for compute
TRT_DTYPE="${TRT_DTYPE:-float16}"

# KV cache GPU fraction = CHAT_GPU_FRAC
# 0.70 when both chat+tool deployed, 0.90 when chat-only
if [ -z "${TRT_KV_FREE_GPU_FRAC:-}" ]; then
  TRT_KV_FREE_GPU_FRAC="${CHAT_GPU_FRAC:-0.70}"
fi

TRT_KV_ENABLE_BLOCK_REUSE="${TRT_KV_ENABLE_BLOCK_REUSE:-0}"

# =============================================================================
# QUANTIZATION PARAMETERS (aligned with vLLM AWQ defaults from calibration.py)
# =============================================================================

# AWQ block size (q_group_size): 128 matches vLLM AWQ
TRT_AWQ_BLOCK_SIZE="${TRT_AWQ_BLOCK_SIZE:-128}"

# Calibration samples: 64 matches vLLM AWQ nsamples default
# For larger models or those needing more calibration data, increase
TRT_CALIB_SIZE="${TRT_CALIB_SIZE:-64}"

# Calibration batch size: dynamically set based on model profile
# Gemma/heavy models: smaller batch (8), standard models: 16
TRT_CALIB_BATCH_SIZE="${TRT_CALIB_BATCH_SIZE:-}"

# Calibration sequence length: derived from CHAT_MAX_LEN + CHAT_MAX_OUT
# vLLM default is 2048, but we use our actual context window
if [ -z "${TRT_CALIB_SEQLEN:-}" ]; then
  _chat_max_len="${CHAT_MAX_LEN:-5525}"
  _chat_max_out="${CHAT_MAX_OUT:-150}"
  TRT_CALIB_SEQLEN=$(( _chat_max_len + _chat_max_out ))
fi

# =============================================================================
# DIRECTORY PATHS
# =============================================================================

TRT_CHECKPOINT_DIR="${TRT_CHECKPOINT_DIR:-}"
TRT_ENGINE_DIR="${TRTLLM_ENGINE_DIR:-}"
TRT_CACHE_DIR="${TRT_CACHE_DIR:-${ROOT_DIR:-.}/.trt_cache}"
TRT_MODELS_DIR="${TRT_MODELS_DIR:-${ROOT_DIR:-.}/models}"

# =============================================================================
# HUGGING FACE PUSH SETTINGS
# =============================================================================
# Push is controlled by --push-quant flag (sets HF_AWQ_PUSH=1)
# HF_PUSH_REPO_ID must be set when --push-quant is used
# HF_PUSH_PRIVATE controls whether repo is private (1) or public (0)

# Note: These are defined in common params, just re-export for TRT context

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Resolve calibration batch size based on model characteristics
# Heavy models (Gemma, large MoE) need smaller batch sizes to avoid OOM
trt_resolve_calib_batch_size() {
  local model_id="${1:-}"
  local default_batch="${2:-16}"
  
  # If explicitly set, use that
  if [ -n "${TRT_CALIB_BATCH_SIZE:-}" ]; then
    echo "${TRT_CALIB_BATCH_SIZE}"
    return
  fi
  
  local model_lower
  model_lower="$(echo "${model_id}" | tr '[:upper:]' '[:lower:]')"
  
  # Heavy models that need smaller calibration batch
  case "${model_lower}" in
    *gemma*|*mixtral*|*qwen3-next*|*moonlight*|*deepseek*)
      echo "8"
      ;;
    *)
      echo "${default_batch}"
      ;;
  esac
}

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
# 8bit -> fp8 on L40S/H100, int8_sq on A100
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
    fp8)
      echo "fp8"
      ;;
    *)
      echo "int8"
      ;;
  esac
}

# Log the derived TRT configuration
trt_log_config() {
  log_info "[trt] TRT-LLM Configuration:"
  log_info "[trt]   Max batch size: ${TRT_MAX_BATCH_SIZE:-<not set>}"
  log_info "[trt]   Max input length: ${TRT_MAX_INPUT_LEN}"
  log_info "[trt]   Max output length: ${TRT_MAX_OUTPUT_LEN}"
  log_info "[trt]   KV cache GPU fraction: ${TRT_KV_FREE_GPU_FRAC}"
  log_info "[trt]   GPU SM arch: ${GPU_SM_ARCH:-auto-detect}"
}

# Validate TRT_MAX_BATCH_SIZE is set (called before engine build)
trt_validate_batch_size() {
  if [ -z "${TRT_MAX_BATCH_SIZE:-}" ]; then
    log_err "[trt] TRT_MAX_BATCH_SIZE must be set when building a TRT engine."
    log_err "[trt] This value is baked into the compiled engine and determines the maximum"
    log_err "[trt] number of sequences that can be batched together in a single forward pass."
    log_err "[trt] "
    log_err "[trt] Example values based on model size:"
    log_err "[trt]   - 7-8B models: 32-64"
    log_err "[trt]   - 13B models: 16-32"
    log_err "[trt]   - 70B+ models: 8-16"
    log_err "[trt] "
    log_err "[trt] Set it via: export TRT_MAX_BATCH_SIZE=<value>"
    return 1
  fi
  
  # Validate it's a positive integer
  if ! [[ "${TRT_MAX_BATCH_SIZE}" =~ ^[1-9][0-9]*$ ]]; then
    log_err "[trt] TRT_MAX_BATCH_SIZE must be a positive integer, got: ${TRT_MAX_BATCH_SIZE}"
    return 1
  fi
  
  log_info "[trt] TRT_MAX_BATCH_SIZE=${TRT_MAX_BATCH_SIZE} (will be baked into engine)"
  return 0
}

# Export all TRT environment variables
trt_export_env() {
  export TRT_VERSION TRT_PIP_SPEC TRT_EXTRA_INDEX_URL
  export TRT_PYTORCH_VERSION TRT_TORCHVISION_VERSION TRT_PYTORCH_INDEX_URL
  export MPI_VERSION_PIN NEED_MPI
  export TRT_REPO_URL TRT_REPO_TAG TRT_REPO_DIR
  export GPU_SM_ARCH TRT_FP8_SM_ARCHS
  export TRT_MAX_BATCH_SIZE TRT_MAX_INPUT_LEN TRT_MAX_OUTPUT_LEN TRT_DTYPE
  export TRT_KV_FREE_GPU_FRAC TRT_KV_ENABLE_BLOCK_REUSE
  export TRT_AWQ_BLOCK_SIZE TRT_CALIB_SIZE TRT_CALIB_BATCH_SIZE TRT_CALIB_SEQLEN
  export TRT_CHECKPOINT_DIR TRT_ENGINE_DIR TRT_CACHE_DIR TRT_MODELS_DIR
}
