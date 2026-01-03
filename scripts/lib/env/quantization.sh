#!/usr/bin/env bash
# =============================================================================
# Quantization Environment Setup
# =============================================================================
# GPU-specific quantization defaults for vLLM deployments.
# Configures KV cache dtype, attention backend, and memory settings based on
# GPU architecture and selected quantization method.

# =============================================================================
# HuggingFace Environment Setup
# =============================================================================

awq_setup_hf_env() {
  export HF_HOME="${HF_HOME:-${ROOT_DIR}/.hf}"
  export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-${HF_HOME}/hub}"
  if [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
    export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"
  fi
  export HF_HUB_DISABLE_TELEMETRY=1
  # Respect user override; default to disabled to avoid DNS issues with xet endpoints
  export HF_HUB_ENABLE_HF_TRANSFER=${HF_HUB_ENABLE_HF_TRANSFER:-0}
}

# =============================================================================
# GPU-SPECIFIC HELPER FUNCTIONS
# =============================================================================

# Apply defaults for Hopper/Ada GPUs (H100, L40S)
# These GPUs support native FP8 compute and FP8 KV cache
_apply_hopper_ada_defaults() {
  local gpu_name="${1:-}"
  export KV_DTYPE=${KV_DTYPE:-fp8}
  export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
  export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-256}
  export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-224}
  export PYTORCH_ALLOC_CONF=expandable_segments:True
  # Set architecture: H100 = 9.0, L40S/Ada = 8.9
  if [[ "${gpu_name}" == *H100* ]]; then
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
  else
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
  fi
}

# Apply defaults for A100 GPUs
# A100 uses INT8 KV cache (no native FP8 KV support)
_apply_a100_defaults() {
  export KV_DTYPE=${KV_DTYPE:-int8}
  export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
  export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
  export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-256}
  export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-224}
  export PYTORCH_ALLOC_CONF=expandable_segments:True
  export CUDA_DEVICE_MAX_CONNECTIONS=1
}

# Apply FlashInfer or fallback to XFORMERS based on availability
_apply_attention_backend() {
  local use_v1_default="${1:-1}"
  if [ "${HAS_FLASHINFER}" = "1" ]; then
    export VLLM_USE_V1=${VLLM_USE_V1:-${use_v1_default}}
    export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
  else
    export VLLM_USE_V1=${VLLM_USE_V1:-0}
    export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
  fi
}

# Apply conservative defaults for unknown GPUs
_apply_unknown_gpu_defaults() {
  export KV_DTYPE=${KV_DTYPE:-auto}
  export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
}

# =============================================================================
# QUANTIZATION-SPECIFIC DEFAULTS
# =============================================================================

# Apply FP8 quantization defaults based on GPU
_apply_fp8_defaults() {
  local gpu_name="${1:-}"
  case "${gpu_name}" in
    *H100*|*L40S*|*L40*)
      _apply_hopper_ada_defaults "${gpu_name}"
      export TOOL_TIMEOUT_S=${TOOL_TIMEOUT_S:-10}
      export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-256}
      export GEN_TIMEOUT_S=${GEN_TIMEOUT_S:-60}
      ;;
    *A100*)
      _apply_a100_defaults
      _apply_attention_backend 1
      export TOOL_TIMEOUT_S=${TOOL_TIMEOUT_S:-10}
      export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-1000}
      export GEN_TIMEOUT_S=${GEN_TIMEOUT_S:-60}
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
    *H100*|*L40S*|*L40*)
      export VLLM_USE_V1=1
      _apply_hopper_ada_defaults "${gpu_name}"
      if [ "${HAS_FLASHINFER}" = "1" ]; then
        export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
      else
        export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
        if [ "${INFERENCE_ENGINE:-vllm}" != "trt" ]; then
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
    *H100*|*L40S*|*L40*)
      export VLLM_USE_V1=1
      export KV_DTYPE=${KV_DTYPE:-fp8}
      if [[ "${gpu_name}" == *H100* ]]; then
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
      else
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
      fi
      log_info "[env] Hopper/Ada 4-bit mode: V1 engine preferred; backend decided in Python"
      ;;
    *)
      export VLLM_USE_V1=0
      export VLLM_ATTENTION_BACKEND=XFORMERS
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
  echo "fp8"
}

# Resolve effective quantization from QUANTIZATION and CHAT_QUANTIZATION
_resolve_effective_quantization() {
  local effective_quant="${QUANTIZATION:-}"
  
  # Prefer CHAT_QUANTIZATION when it's more specific
  if [ -z "${effective_quant}" ] || [ "${effective_quant}" = "8bit" ] || [ "${effective_quant}" = "fp8" ] || [ "${effective_quant}" = "int8" ]; then
    if [ -n "${CHAT_QUANTIZATION:-}" ]; then
      case "${CHAT_QUANTIZATION}" in
        awq|gptq|gptq_marlin)
          # 4-bit methods always take precedence
          effective_quant="${CHAT_QUANTIZATION}"
          ;;
        8bit|fp8|int8)
          # 8-bit variants: use CHAT_QUANTIZATION if QUANTIZATION was a placeholder
          if [ -z "${effective_quant}" ] || [ "${effective_quant}" = "8bit" ]; then
            effective_quant="${CHAT_QUANTIZATION}"
          fi
          ;;
      esac
    fi
  fi
  
  # Default to 8bit placeholder if still unset
  if [ -z "${effective_quant}" ]; then
    effective_quant="8bit"
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
  if [ "${effective_quant}" = "8bit" ]; then
    effective_quant="$(_resolve_8bit_backend)"
    export QUANTIZATION="${effective_quant}"
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
  export KV_DTYPE=${KV_DTYPE:-auto}
  export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
}
