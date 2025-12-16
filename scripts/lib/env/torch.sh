#!/usr/bin/env bash

# Torch/CUDA environment utilities

ensure_torch_cuda_arch_list() {
  if [ -z "${TORCH_CUDA_ARCH_LIST:-}" ]; then
    if command -v nvidia-smi >/dev/null 2>&1; then
      CAP=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -n 1 2>/dev/null || true)
      if [ -n "${CAP}" ]; then
        export TORCH_CUDA_ARCH_LIST="${CAP}"
        log_info "Detected compute capability: ${TORCH_CUDA_ARCH_LIST}"
      else
        export TORCH_CUDA_ARCH_LIST=8.0
        log_warn "Could not detect compute capability; defaulting TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}"
      fi
    else
      export TORCH_CUDA_ARCH_LIST=8.0
      log_warn "nvidia-smi not found; defaulting TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}"
    fi
  fi
}


