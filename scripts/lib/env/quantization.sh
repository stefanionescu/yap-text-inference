#!/usr/bin/env bash

# Apply quantization- and GPU-specific defaults

apply_quantization_defaults() {
  local gpu_name="${DETECTED_GPU_NAME:-}"
  local effective_quant="${QUANTIZATION:-}"
  if [ -z "${effective_quant}" ] || [ "${effective_quant}" = "fp8" ]; then
    if [ -n "${CHAT_QUANTIZATION:-}" ] && [ "${CHAT_QUANTIZATION}" != "fp8" ]; then
      effective_quant="${CHAT_QUANTIZATION}"
    elif [ -n "${TOOL_QUANTIZATION:-}" ] && [ "${TOOL_QUANTIZATION}" != "fp8" ]; then
      effective_quant="${TOOL_QUANTIZATION}"
    fi
  fi
  if [ -z "${effective_quant}" ]; then
    effective_quant="fp8"
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
          export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
          export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
          export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
          export TOOL_HARD_TIMEOUT_MS=${TOOL_HARD_TIMEOUT_MS:-500}
          export TOOL_TIMEOUT_S=${TOOL_TIMEOUT_S:-0.5}
          export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-256}
          export GEN_TIMEOUT_S=${GEN_TIMEOUT_S:-60}
          ;;
        *A100*)
          export VLLM_USE_V1=0
          export KV_DTYPE=${KV_DTYPE:-int8}
          export VLLM_ATTENTION_BACKEND=XFORMERS
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
          export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
          export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
          export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
          export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
          export CUDA_DEVICE_MAX_CONNECTIONS=1
          export TOOL_HARD_TIMEOUT_MS=${TOOL_HARD_TIMEOUT_MS:-500}
          export TOOL_TIMEOUT_S=${TOOL_TIMEOUT_S:-0.5}
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
            log_warn "FlashInfer not available; using XFORMERS backend for AWQ."
          fi
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
          if [[ "${gpu_name}" == *H100* ]]; then
            export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
          fi
          export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
          export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
          export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
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
          export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
          export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
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
          export VLLM_USE_V1=0
          export KV_DTYPE=${KV_DTYPE:-int8}
          export VLLM_ATTENTION_BACKEND=XFORMERS
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
          log_info "A100 4-bit mode: V0 engine + INT8 KV for maximum context slots"
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


