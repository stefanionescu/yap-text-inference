#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${SCRIPT_DIR}/../lib/common/log.sh"

log_info "[gpu] Checking GPU availability"
if ! command -v nvidia-smi >/dev/null 2>&1; then
  log_warn "[gpu] nvidia-smi not found; ensure this RunPod image has NVIDIA drivers."
elif ! nvidia-smi >/dev/null 2>&1; then
  log_warn "[gpu] nvidia-smi failed; GPU may not be available."
else
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 || echo "Unknown")
  log_info "[gpu] GPU detected: ${GPU_NAME}"
fi

# Print CUDA/Torch ABI hint if available
if [ -d "${ROOT_DIR}/.venv" ]; then
  CU_VER=$("${ROOT_DIR}/.venv/bin/python" - <<'PY' || true
import sys
try:
    import torch
    print((torch.version.cuda or '').strip())
except Exception:
    sys.exit(1)
PY
  )
  if [ -n "${CU_VER:-}" ]; then
    log_info "[gpu] Torch CUDA version detected: ${CU_VER}"
  fi
fi


