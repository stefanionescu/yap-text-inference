#!/usr/bin/env bash

# Apply quantization- and GPU-specific defaults

# Resolve "8bit" placeholder to actual backend (fp8 or int8) based on GPU
_resolve_8bit_backend() {
  local gpu_name="${1:-}"
  case "${gpu_name}" in
    *H100*|*L40S*|*L40*)
      # Hopper/Ada: native FP8 support
      echo "fp8"
      ;;
    *A100*)
      # Ampere: no FP8, use INT8
      echo "int8"
      ;;
    *)
      # Unknown GPU: default to fp8 (will work in emulated mode on most GPUs)
      echo "fp8"
      ;;
  esac
}

apply_quantization_defaults() {
  local gpu_name="${DETECTED_GPU_NAME:-}"
  if [ "${DEPLOY_CHAT:-0}" != "1" ]; then
    log_info "Skipping vLLM quantization defaults (chat engine disabled)"
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
    log_info "Resolved 8-bit quantization to '${effective_quant}' for GPU: ${gpu_name:-unknown}"
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
          export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
          export TOOL_TIMEOUT_S=${TOOL_TIMEOUT_S:-10}
          export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-256}
          export GEN_TIMEOUT_S=${GEN_TIMEOUT_S:-60}
          log_info "FP8 mode: Hopper/Ada GPU with native FP8 support"
          ;;
        *A100*)
          # A100 can't do native FP8, but Marlin can run FP8 weights in W8A16 emulated mode
          # This shouldn't happen if 8bit was properly resolved to int8, but handle it gracefully
          log_warn "FP8 requested on A100 (no native FP8). Using W8A16 emulated mode. Consider using INT8 instead."
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
          export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
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
    int8)
      # INT8 weight quantization (W8A8) - native on A100 and newer
      case "${gpu_name}" in
        *A100*)
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
          export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
          export CUDA_DEVICE_MAX_CONNECTIONS=1
          export TOOL_TIMEOUT_S=${TOOL_TIMEOUT_S:-10}
          export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-1000}
          export GEN_TIMEOUT_S=${GEN_TIMEOUT_S:-60}
          log_info "INT8 mode: A100 with native INT8 tensor cores"
          ;;
        *H100*|*L40S*|*L40*)
          # H100/L40 can do INT8 too, but FP8 is usually better
          log_info "INT8 requested on Hopper/Ada GPU (FP8 might be faster, but INT8 works fine)"
          export KV_DTYPE=${KV_DTYPE:-int8}
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
          if [[ "${gpu_name}" == *H100* ]]; then
            export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
          fi
          export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
          export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-256}
          export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-224}
          export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
          ;;
        *)
          export KV_DTYPE=${KV_DTYPE:-int8}
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
          log_info "INT8 mode: using INT8 weight quantization with INT8 KV cache"
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
            log_warn "FlashInfer not available; using XFORMERS backend for AWQ."
          fi
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
          if [[ "${gpu_name}" == *H100* ]]; then
            export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
          fi
          export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
          export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-256}
          export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-224}
          export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
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
          export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
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
            log_info "A100 4-bit mode: V1 engine + FlashInfer + INT8 KV"
          else
            export VLLM_USE_V1=0
            export VLLM_ATTENTION_BACKEND=XFORMERS
            log_info "A100 4-bit mode: V0 engine + XFORMERS + INT8 KV"
          fi
          ;;
        *H100*|*L40S*|*L40*)
          export VLLM_USE_V1=1
          export KV_DTYPE=${KV_DTYPE:-fp8}
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
          if [[ "${gpu_name}" == *H100* ]]; then
            export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
          fi
          log_info "Hopper/Ada 4-bit mode: V1 engine preferred; backend decided in Python"
          ;;
        *)
          export VLLM_USE_V1=0
          export KV_DTYPE=${KV_DTYPE:-auto}
          export VLLM_ATTENTION_BACKEND=XFORMERS
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
          log_warn "Unknown GPU 4-bit mode: using conservative V0 + fp16 KV"
          ;;
      esac
      ;;
  esac

  # Final defaults if still unset
  export KV_DTYPE=${KV_DTYPE:-auto}
  export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
}


