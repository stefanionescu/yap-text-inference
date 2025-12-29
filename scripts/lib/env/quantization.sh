#!/usr/bin/env bash

# Quantization environment setup and GPU-specific defaults

# =============================================================================
# HuggingFace Environment Setup for Quantization
# =============================================================================

awq_setup_hf_env() {
  export HF_HOME="${HF_HOME:-${ROOT_DIR}/.hf}"
  export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-${HF_HOME}/hub}"
  if [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
    export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}"
  fi
  export HF_HUB_DISABLE_TELEMETRY=1
  # Respect user override; default to disabled to avoid DNS issues with xet transfer endpoints
  export HF_HUB_ENABLE_HF_TRANSFER=${HF_HUB_ENABLE_HF_TRANSFER:-0}
}

# =============================================================================
# GPU-Specific Quantization Defaults
# =============================================================================

# Apply quantization- and GPU-specific defaults

# Resolve "8bit" placeholder to actual backend based on GPU
# Note: vLLM uses "fp8" for 8-bit weight quantization on ALL GPUs
# - On H100/Ada: native FP8 compute
# - On A100: W8A16 emulated mode (FP8 weights, FP16 compute via Marlin)
# The difference is in KV cache: FP8 on H100/Ada, INT8 on A100
_resolve_8bit_backend() {
  local gpu_name="${1:-}"
  # vLLM only supports "fp8" for on-the-fly 8-bit weight quantization
  # It works on A100 via W8A16 Marlin (emulated mode)
  echo "fp8"
}

apply_quantization_defaults() {
  local gpu_name="${DETECTED_GPU_NAME:-}"
  if [ "${DEPLOY_CHAT:-0}" != "1" ]; then
    log_info "[env] Skipping vLLM quantization defaults (chat engine disabled)"
    return
  fi
  local effective_quant="${QUANTIZATION:-}"
  # Prefer CHAT_QUANTIZATION when it's more specific than the base QUANTIZATION
  if [ -z "${effective_quant}" ] || [ "${effective_quant}" = "8bit" ] || [ "${effective_quant}" = "fp8" ] || [ "${effective_quant}" = "int8" ]; then
    if [ -n "${CHAT_QUANTIZATION:-}" ]; then
      # Only override if CHAT_QUANTIZATION specifies a different 8-bit variant or 4-bit method
      case "${CHAT_QUANTIZATION}" in
        awq|gptq|gptq_marlin)
          # 4-bit methods always take precedence
          effective_quant="${CHAT_QUANTIZATION}"
          ;;
        8bit|fp8|int8)
          # 8-bit variants: use CHAT_QUANTIZATION if QUANTIZATION was just a placeholder
          if [ -z "${effective_quant}" ] || [ "${effective_quant}" = "8bit" ]; then
            effective_quant="${CHAT_QUANTIZATION}"
          fi
          ;;
      esac
    fi
  fi
  if [ -z "${effective_quant}" ]; then
    # Default to 8bit placeholder; resolved based on GPU below
    effective_quant="8bit"
  fi

  # Resolve "8bit" placeholder to actual backend based on GPU architecture
  if [ "${effective_quant}" = "8bit" ]; then
    effective_quant="$(_resolve_8bit_backend "${gpu_name}")"
    export QUANTIZATION="${effective_quant}"
    export CHAT_QUANTIZATION="${effective_quant}"
    log_info "[env] Resolved 8-bit quantization to '${effective_quant}' for GPU: ${gpu_name:-unknown}"
  fi

  case "${effective_quant}" in
    fp8)
      case "${gpu_name}" in
        *H100*|*L40S*|*L40*)
          export KV_DTYPE=${KV_DTYPE:-fp8}
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
          if [[ "${gpu_name}" == *H100* ]]; then
            export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
          fi
          export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
          export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-256}
          export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-224}
          export PYTORCH_ALLOC_CONF=expandable_segments:True
          export TOOL_TIMEOUT_S=${TOOL_TIMEOUT_S:-10}
          export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-256}
          export GEN_TIMEOUT_S=${GEN_TIMEOUT_S:-60}
          ;;
        *A100*)
          # A100 runs FP8 weights in W8A16 emulated mode via Marlin (stores FP8, computes FP16)
          # KV cache uses INT8 since A100 doesn't support FP8 KV cache
          export KV_DTYPE=${KV_DTYPE:-int8}
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
          if [ "${HAS_FLASHINFER}" = "1" ]; then
            export VLLM_USE_V1=1
            export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
          else
            export VLLM_USE_V1=0
            export VLLM_ATTENTION_BACKEND=XFORMERS
          fi
          export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
          export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-256}
          export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-224}
          export PYTORCH_ALLOC_CONF=expandable_segments:True
          export CUDA_DEVICE_MAX_CONNECTIONS=1
          export TOOL_TIMEOUT_S=${TOOL_TIMEOUT_S:-10}
          export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-1000}
          export GEN_TIMEOUT_S=${GEN_TIMEOUT_S:-60}
          ;;
        *)
          export KV_DTYPE=${KV_DTYPE:-auto}
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
          ;;
      esac
      ;;
    awq)
      case "${gpu_name}" in
        *H100*|*L40S*|*L40*)
          export VLLM_USE_V1=1
          export KV_DTYPE=${KV_DTYPE:-fp8}
          if [ "${HAS_FLASHINFER}" = "1" ]; then
            export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
          else
            export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
            if [ "${INFERENCE_ENGINE:-vllm}" != "trt" ]; then
              log_warn "[env] ⚠ FlashInfer not available; using XFORMERS backend for AWQ."
            fi
          fi
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
          if [[ "${gpu_name}" == *H100* ]]; then
            export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
          fi
          export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
          export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-256}
          export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-224}
          export PYTORCH_ALLOC_CONF=expandable_segments:True
          ;;
        *A100*)
          if [ "${HAS_FLASHINFER}" = "1" ]; then
            export VLLM_USE_V1=1
            export KV_DTYPE=${KV_DTYPE:-int8}
            export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
          else
            export VLLM_USE_V1=0
            export KV_DTYPE=${KV_DTYPE:-int8}
            export VLLM_ATTENTION_BACKEND=XFORMERS
          fi
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
          export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
          export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-256}
          export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-224}
          export PYTORCH_ALLOC_CONF=expandable_segments:True
          export CUDA_DEVICE_MAX_CONNECTIONS=1
          ;;
        *)
          export VLLM_USE_V1=${VLLM_USE_V1:-1}
          export KV_DTYPE=${KV_DTYPE:-auto}
          if [ "${HAS_FLASHINFER}" = "1" ]; then
            export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
          else
            export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
          fi
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
          ;;
      esac
      ;;
    gptq_marlin)
      case "${gpu_name}" in
        *A100*)
          # A100 can't do FP8 KV cache, but FlashInfer works fine with int8
          export KV_DTYPE=${KV_DTYPE:-int8}
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
          if [ "${HAS_FLASHINFER}" = "1" ]; then
            export VLLM_USE_V1=1
            export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
          else
            export VLLM_USE_V1=0
            export VLLM_ATTENTION_BACKEND=XFORMERS
          fi
          ;;
        *H100*|*L40S*|*L40*)
          export VLLM_USE_V1=1
          export KV_DTYPE=${KV_DTYPE:-fp8}
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
          if [[ "${gpu_name}" == *H100* ]]; then
            export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
          fi
          log_info "[env] Hopper/Ada 4-bit mode: V1 engine preferred; backend decided in Python"
          ;;
        *)
          export VLLM_USE_V1=0
          export KV_DTYPE=${KV_DTYPE:-auto}
          export VLLM_ATTENTION_BACKEND=XFORMERS
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
          log_warn "[env] ⚠ Unknown GPU 4-bit mode: using conservative V0 + fp16 KV"
          ;;
      esac
      ;;
  esac

  log_blank

  # Final defaults if still unset
  export KV_DTYPE=${KV_DTYPE:-auto}
  export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
}
