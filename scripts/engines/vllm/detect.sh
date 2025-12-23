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
  
  "${python_exec}" - <<'PY' 2>/dev/null || true
import sys
try:
    import torch
    cu = (torch.version.cuda or '').strip()
    if not cu:
        sys.exit(1)
    print(cu.replace('.', ''))  # e.g., 12.6 -> 126
except Exception:
    sys.exit(1)
PY
}

# Detect torch major.minor version (for FlashInfer wheel selection)
vllm_detect_torch_version() {
  local python_exec="${1:-python}"
  
  "${python_exec}" - <<'PY' 2>/dev/null || true
import sys
try:
    import torch
    ver = torch.__version__.split('+', 1)[0]
    parts = ver.split('.')
    print(f"{parts[0]}.{parts[1]}")  # e.g., 2.9.0 -> 2.9
except Exception:
    sys.exit(1)
PY
}

# Check if vLLM is installed
vllm_is_installed() {
  local python_exec="${1:-python}"
  
  if "${python_exec}" -c "import vllm" 2>/dev/null; then
    return 0
  fi
  return 1
}

# Get vLLM version
vllm_get_version() {
  local python_exec="${1:-python}"
  
  "${python_exec}" - <<'PY' 2>/dev/null || echo "unknown"
try:
    import vllm
    print(vllm.__version__)
except Exception:
    print("unknown")
PY
}

