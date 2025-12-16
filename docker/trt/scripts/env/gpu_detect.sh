#!/usr/bin/env bash

# GPU detection for TRT-LLM

GPU_NAME=""
GPU_SM=""

if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 || true)
  
  # Get compute capability for SM architecture
  cap=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n1 || true)
  if [ -n "${cap}" ]; then
    GPU_SM="sm${cap/./}"
  fi
fi

export DETECTED_GPU_NAME="${GPU_NAME}"
export GPU_SM_ARCH="${GPU_SM}"

# Set GPU-specific defaults
case "${GPU_NAME}" in
  *H100*)
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
    export PYTORCH_ALLOC_CONF=expandable_segments:True
    ;;
  *L40S*|*L40*)
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
    export PYTORCH_ALLOC_CONF=expandable_segments:True
    ;;
  *A100*)
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
    export PYTORCH_ALLOC_CONF=expandable_segments:True
    export CUDA_DEVICE_MAX_CONNECTIONS=1
    ;;
  *)
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
    ;;
esac

