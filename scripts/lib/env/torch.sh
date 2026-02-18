#!/usr/bin/env bash
# =============================================================================
# PyTorch/CUDA Configuration
# =============================================================================
# Configures TORCH_CUDA_ARCH_LIST and detects PyTorch CUDA versions.
# Ensures correct CUDA architecture settings for GPU compilation.

_TORCH_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/quantization.sh
source "${_TORCH_ENV_DIR}/../../config/values/quantization.sh"

ensure_torch_cuda_arch_list() {
  if [ -z "${TORCH_CUDA_ARCH_LIST:-}" ]; then
    if command -v nvidia-smi >/dev/null 2>&1; then
      CAP=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -n 1 2>/dev/null || true)
      if [ -n "${CAP}" ]; then
        export TORCH_CUDA_ARCH_LIST="${CAP}"
        log_info "[gpu] Detected compute capability: ${TORCH_CUDA_ARCH_LIST}"
      else
        export TORCH_CUDA_ARCH_LIST="${CFG_QUANT_TORCH_ARCH_A100}"
        log_warn "[gpu] ⚠ Could not detect compute capability; defaulting TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}"
      fi
    else
      export TORCH_CUDA_ARCH_LIST="${CFG_QUANT_TORCH_ARCH_A100}"
      log_warn "[gpu] ⚠ nvidia-smi not found; defaulting TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}"
    fi
  fi
}
