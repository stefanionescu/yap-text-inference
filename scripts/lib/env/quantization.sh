#!/usr/bin/env bash
# =============================================================================
# Quantization Environment Setup
# =============================================================================
# GPU-specific quantization defaults for vLLM deployments.
# Configures KV cache dtype, attention backend, and memory settings based on
# GPU architecture and selected quantization method.

_QUANT_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/core.sh
source "${_QUANT_ENV_DIR}/../../config/values/core.sh"
# shellcheck source=../../config/values/quantization.sh
source "${_QUANT_ENV_DIR}/../../config/values/quantization.sh"
# shellcheck source=../../config/patterns.sh
source "${_QUANT_ENV_DIR}/../../config/patterns.sh"

# =============================================================================
# HuggingFace Environment Setup
# =============================================================================

awq_setup_hf_env() {
  export HF_HOME="${HF_HOME:-${ROOT_DIR}/.hf}"
  export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-${HF_HOME}/hub}"
  if [ -f "${CFG_HF_CA_CERTS_PATH}" ]; then
    export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-${CFG_HF_CA_CERTS_PATH}}"
  fi
  export HF_HUB_DISABLE_TELEMETRY="${CFG_HF_HUB_DISABLE_TELEMETRY}"
  # Respect user override; default to disabled to avoid DNS issues with xet endpoints
  export HF_HUB_ENABLE_HF_TRANSFER="${HF_HUB_ENABLE_HF_TRANSFER:-${CFG_HF_HUB_ENABLE_HF_TRANSFER_DEFAULT}}"
}

# =============================================================================
# GPU-SPECIFIC HELPER FUNCTIONS
# =============================================================================

# Apply defaults for Hopper/Ada GPUs (H100, L40S)
# These GPUs support native FP8 compute and FP8 KV cache
_apply_hopper_ada_defaults() {
  local gpu_name="${1:-}"
  export KV_DTYPE="${KV_DTYPE:-${CFG_QUANT_KV_DTYPE_FP8}}"
  export ENFORCE_EAGER="${ENFORCE_EAGER:-${CFG_QUANT_ENFORCE_EAGER_DEFAULT}}"
  export MAX_NUM_BATCHED_TOKENS_CHAT="${MAX_NUM_BATCHED_TOKENS_CHAT:-${CFG_QUANT_MAX_BATCHED_TOKENS_CHAT}}"
  export MAX_NUM_BATCHED_TOKENS_TOOL="${MAX_NUM_BATCHED_TOKENS_TOOL:-${CFG_QUANT_MAX_BATCHED_TOKENS_TOOL}}"
  export PYTORCH_ALLOC_CONF="${CFG_QUANT_PYTORCH_ALLOC_CONF}"
  # Set architecture: H100 = 9.0, L40S/Ada = 8.9
  if [[ ${gpu_name} == *H100* ]]; then
    export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-${CFG_QUANT_TORCH_ARCH_H100}}"
  else
    export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-${CFG_QUANT_TORCH_ARCH_ADA}}"
  fi
}

# Apply defaults for A100 GPUs
# A100 uses INT8 KV cache (no native FP8 KV support)
_apply_a100_defaults() {
  export KV_DTYPE="${KV_DTYPE:-${CFG_QUANT_KV_DTYPE_INT8}}"
  export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-${CFG_QUANT_TORCH_ARCH_A100}}"
  export ENFORCE_EAGER="${ENFORCE_EAGER:-${CFG_QUANT_ENFORCE_EAGER_DEFAULT}}"
  export MAX_NUM_BATCHED_TOKENS_CHAT="${MAX_NUM_BATCHED_TOKENS_CHAT:-${CFG_QUANT_MAX_BATCHED_TOKENS_CHAT}}"
  export MAX_NUM_BATCHED_TOKENS_TOOL="${MAX_NUM_BATCHED_TOKENS_TOOL:-${CFG_QUANT_MAX_BATCHED_TOKENS_TOOL}}"
  export PYTORCH_ALLOC_CONF="${CFG_QUANT_PYTORCH_ALLOC_CONF}"
  export CUDA_DEVICE_MAX_CONNECTIONS="${CFG_QUANT_CUDA_DEVICE_MAX_CONNECTIONS}"
}

# Apply FlashInfer or fallback to XFORMERS based on availability
_apply_attention_backend() {
  local use_v1_default="${1:-1}"
  if [ "${HAS_FLASHINFER}" = "1" ]; then
    export VLLM_USE_V1=${VLLM_USE_V1:-${use_v1_default}}
    export VLLM_ATTENTION_BACKEND="${VLLM_ATTENTION_BACKEND:-${CFG_QUANT_BACKEND_FLASHINFER}}"
  else
    export VLLM_USE_V1=${VLLM_USE_V1:-0}
    export VLLM_ATTENTION_BACKEND="${VLLM_ATTENTION_BACKEND:-${CFG_QUANT_BACKEND_XFORMERS}}"
  fi
}

# Apply conservative defaults for unknown GPUs
_apply_unknown_gpu_defaults() {
  export KV_DTYPE="${KV_DTYPE:-${CFG_QUANT_KV_DTYPE_AUTO}}"
  export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-${CFG_QUANT_TORCH_ARCH_A100}}"
}

# =============================================================================
# QUANTIZATION-SPECIFIC DEFAULTS
# =============================================================================

# Apply FP8 quantization defaults based on GPU
_apply_fp8_defaults() {
  local gpu_name="${1:-}"
  case "${gpu_name}" in
    *H100* | *L40S* | *L40*)
      _apply_hopper_ada_defaults "${gpu_name}"
      export TOOL_TIMEOUT_S="${TOOL_TIMEOUT_S:-${CFG_QUANT_TOOL_TIMEOUT_S}}"
      export PREBUFFER_MAX_CHARS="${PREBUFFER_MAX_CHARS:-${CFG_QUANT_PREBUFFER_MAX_CHARS_HOPPER}}"
      export GEN_TIMEOUT_S="${GEN_TIMEOUT_S:-${CFG_QUANT_GEN_TIMEOUT_S}}"
      ;;
    *A100*)
      _apply_a100_defaults
      _apply_attention_backend 1
      export TOOL_TIMEOUT_S="${TOOL_TIMEOUT_S:-${CFG_QUANT_TOOL_TIMEOUT_S}}"
      export PREBUFFER_MAX_CHARS="${PREBUFFER_MAX_CHARS:-${CFG_QUANT_PREBUFFER_MAX_CHARS_A100}}"
      export GEN_TIMEOUT_S="${GEN_TIMEOUT_S:-${CFG_QUANT_GEN_TIMEOUT_S}}"
      ;;
    *)
      _apply_unknown_gpu_defaults
      ;;
  esac
}

# Apply AWQ quantization defaults based on GPU
_apply_awq_defaults() {
  local gpu_name="${1:-}"
  case "${gpu_name}" in
    *H100* | *L40S* | *L40*)
      export VLLM_USE_V1=1
      _apply_hopper_ada_defaults "${gpu_name}"
      if [ "${HAS_FLASHINFER}" = "1" ]; then
        export VLLM_ATTENTION_BACKEND="${VLLM_ATTENTION_BACKEND:-${CFG_QUANT_BACKEND_FLASHINFER}}"
      else
        export VLLM_ATTENTION_BACKEND="${VLLM_ATTENTION_BACKEND:-${CFG_QUANT_BACKEND_XFORMERS}}"
        if [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" != "${CFG_ENGINE_TRT}" ]; then
          log_warn "[env] ⚠ FlashInfer not available; using XFORMERS backend for AWQ."
        fi
      fi
      ;;
    *A100*)
      _apply_a100_defaults
      _apply_attention_backend 1
      ;;
    *)
      export VLLM_USE_V1=${VLLM_USE_V1:-1}
      _apply_unknown_gpu_defaults
      _apply_attention_backend 1
      ;;
  esac
}

# Apply GPTQ/Marlin quantization defaults based on GPU
_apply_gptq_defaults() {
  local gpu_name="${1:-}"
  case "${gpu_name}" in
    *A100*)
      _apply_a100_defaults
      _apply_attention_backend 1
      ;;
    *H100* | *L40S* | *L40*)
      export VLLM_USE_V1=1
      export KV_DTYPE="${KV_DTYPE:-${CFG_QUANT_KV_DTYPE_FP8}}"
      if [[ ${gpu_name} == *H100* ]]; then
        export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-${CFG_QUANT_TORCH_ARCH_H100}}"
      else
        export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-${CFG_QUANT_TORCH_ARCH_ADA}}"
      fi
      log_info "[env] Hopper/Ada 4-bit mode: V1 engine preferred; backend decided in Python"
      ;;
    *)
      export VLLM_USE_V1=0
      export VLLM_ATTENTION_BACKEND="${CFG_QUANT_BACKEND_XFORMERS}"
      _apply_unknown_gpu_defaults
      log_warn "[env] ⚠ Unknown GPU 4-bit mode: using conservative V0 + fp16 KV"
      ;;
  esac
}

# =============================================================================
# QUANTIZATION RESOLUTION
# =============================================================================

# Resolve "8bit" placeholder to actual backend.
# vLLM uses "fp8" for 8-bit weight quantization on ALL GPUs.
# GPU-specific differences are handled via KV_DTYPE in the apply functions.
_resolve_8bit_backend() {
  echo "${CFG_QUANT_MODE_8BIT_BACKEND}"
}

# Resolve effective quantization from CHAT_QUANTIZATION
_resolve_effective_quantization() {
  local effective_quant="${CHAT_QUANTIZATION:-}"

  # Default to 8bit placeholder if unset
  if [ -z "${effective_quant}" ]; then
    effective_quant="${CFG_QUANT_MODE_8BIT_PLACEHOLDER}"
  fi

  echo "${effective_quant}"
}

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

apply_quantization_defaults() {
  local gpu_name="${DETECTED_GPU_NAME:-}"

  # Skip silently for tool-only mode (no chat engine to configure)
  if [ "${DEPLOY_CHAT:-0}" != "1" ]; then
    return
  fi

  # Resolve effective quantization method
  local effective_quant
  effective_quant="$(_resolve_effective_quantization)"

  # Resolve "8bit" placeholder to actual backend
  if [ "${effective_quant}" = "${CFG_QUANT_MODE_8BIT_PLACEHOLDER}" ]; then
    effective_quant="$(_resolve_8bit_backend)"
    export CHAT_QUANTIZATION="${effective_quant}"
    log_info "[env] Resolved 8-bit quantization to '${effective_quant}'"
  fi

  # Apply quantization-specific GPU defaults
  case "${effective_quant}" in
    fp8)
      _apply_fp8_defaults "${gpu_name}"
      ;;
    awq)
      _apply_awq_defaults "${gpu_name}"
      ;;
    gptq_marlin)
      _apply_gptq_defaults "${gpu_name}"
      ;;
  esac

  # Final fallback defaults if still unset
  export KV_DTYPE="${KV_DTYPE:-${CFG_QUANT_KV_DTYPE_AUTO}}"
  export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-${CFG_QUANT_TORCH_ARCH_A100}}"
}
