#!/usr/bin/env bash
# =============================================================================
# vLLM Detection Utilities
# =============================================================================
# vLLM-specific detection: CUDA/torch version for FlashInfer wheels, vLLM installation.
# GPU detection: use lib/common/gpu_detect.sh functions directly.
# FlashInfer detection: use lib/env/flashinfer.sh functions directly.

_VLLM_DETECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common modules
# shellcheck source=../../lib/common/gpu_detect.sh
source "${_VLLM_DETECT_DIR}/../../lib/common/gpu_detect.sh"
# shellcheck source=../../lib/env/flashinfer.sh
source "${_VLLM_DETECT_DIR}/../../lib/env/flashinfer.sh"

# Detect CUDA version from torch (for FlashInfer wheel selection)
vllm_detect_cuda_version() {
  local python_exec="${1:-python}"
  "${python_exec}" -m src.scripts.vllm.detection cuda-version 2>/dev/null || true
}

# Detect torch major.minor version (for FlashInfer wheel selection)
vllm_detect_torch_version() {
  local python_exec="${1:-python}"
  "${python_exec}" -m src.scripts.vllm.detection torch-version 2>/dev/null || true
}

# Check if vLLM is installed
vllm_is_installed() {
  local python_exec="${1:-python}"
  "${python_exec}" -m src.scripts.vllm.detection is-installed 2>/dev/null
}

# Get vLLM version
vllm_get_version() {
  local python_exec="${1:-python}"
  "${python_exec}" -m src.scripts.vllm.detection version 2>/dev/null || echo "unknown"
}
