#!/usr/bin/env bash
# shellcheck disable=SC1091
# vLLM GPU detection and optimization.
#
# Sources shared GPU detection from common/ and applies vLLM-specific defaults.

_GPU_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find common scripts directory (works in Docker and dev contexts)
if [ -d "/app/common/scripts" ]; then
  _GPU_COMMON_SCRIPTS="/app/common/scripts"
elif [ -d "${_GPU_SCRIPT_DIR}/../../../common/scripts" ]; then
  _GPU_COMMON_SCRIPTS="${_GPU_SCRIPT_DIR}/../../../common/scripts"
else
  echo "[vllm] ERROR: Cannot find common scripts directory" >&2
  exit 1
fi

# Source shared GPU detection
source "${_GPU_COMMON_SCRIPTS}/gpu.sh"

# Initialize GPU detection
gpu_init_detection
gpu_apply_env_defaults

# vLLM-specific GPU optimizations
GPU_NAME="${DETECTED_GPU_NAME:-}"

case "${GPU_NAME}" in
  *H100* | *L40S* | *L40*)
    export VLLM_USE_V1=1
    export KV_DTYPE=${KV_DTYPE:-fp8}
    if [ "${HAS_FLASHINFER:-0}" = "1" ]; then
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
    else
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
      if [ "${INFERENCE_ENGINE:-vllm}" != "trt" ]; then
        log_warn "[vllm] ⚠ FlashInfer not available; using XFORMERS backend for AWQ."
      fi
    fi
    if [[ ${GPU_NAME} == *H100* ]]; then
      export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
    else
      export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
    fi
    export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
    export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-256}
    export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-224}
    export PYTORCH_ALLOC_CONF=expandable_segments:True
    ;;
  *A100*)
    if [ "${HAS_FLASHINFER:-0}" = "1" ]; then
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
    # Unknown GPU: prefer V1; prefer FlashInfer when available
    export VLLM_USE_V1=${VLLM_USE_V1:-1}
    export KV_DTYPE=${KV_DTYPE:-auto}
    if [ "${HAS_FLASHINFER:-0}" = "1" ]; then
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
    else
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
    fi
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
    ;;
esac
