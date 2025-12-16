#!/usr/bin/env bash
# =============================================================================
# vLLM Detection Utilities
# =============================================================================
# Detect FlashInfer availability, CUDA version, and torch compatibility.

# Detect CUDA version from torch
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

# Detect torch major.minor version
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

# Check if FlashInfer is available
vllm_has_flashinfer() {
  local python_exec="${1:-python}"
  
  if "${python_exec}" -c "import flashinfer" 2>/dev/null; then
    return 0
  fi
  return 1
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

# Detect GPU architecture for vLLM
vllm_detect_gpu_arch() {
  local python_exec="${1:-python}"
  
  "${python_exec}" - <<'PY' 2>/dev/null || true
import sys
try:
    import torch
    if not torch.cuda.is_available():
        sys.exit(1)
    cap = torch.cuda.get_device_capability(0)
    print(f"sm{cap[0]}{cap[1]}")  # e.g., sm89
except Exception:
    sys.exit(1)
PY
}

