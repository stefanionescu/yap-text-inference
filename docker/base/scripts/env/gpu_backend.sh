#!/usr/bin/env bash

# GPU detection and backend selection
GPU_NAME=""
if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 || true)
fi
export DETECTED_GPU_NAME="${GPU_NAME}"

case "${QUANTIZATION}" in
  fp8)
    case "${GPU_NAME}" in
      *H100*|*L40S*|*L40*)
        export KV_DTYPE=${KV_DTYPE:-fp8}
        if [ "${HAS_FLASHINFER}" = "1" ]; then
          export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
        else
          export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
          log_warn "FlashInfer not available; using XFORMERS backend for FP8."
        fi
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
        if [[ "${GPU_NAME}" == *H100* ]]; then export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}; fi
        export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
        export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
        export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
        export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
        ;;
      *A100*)
        export VLLM_USE_V1=0
        export KV_DTYPE=${KV_DTYPE:-int8}
        export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
        export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
        export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
        export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
        export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
        export CUDA_DEVICE_MAX_CONNECTIONS=1
        ;;
      *)
        export KV_DTYPE=${KV_DTYPE:-fp8}
        if [ "${HAS_FLASHINFER}" = "1" ]; then
          export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
        else
          export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
        fi
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
        ;;
    esac
    ;;
  gptq|gptq_marlin)
    export QUANTIZATION=gptq_marlin
    export KV_DTYPE=${KV_DTYPE:-fp8}
    if [ "${HAS_FLASHINFER}" = "1" ]; then
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
    else
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
    fi
    ;;
  awq)
    case "${GPU_NAME}" in
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
        if [[ "${GPU_NAME}" == *H100* ]]; then export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}; fi
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
esac


