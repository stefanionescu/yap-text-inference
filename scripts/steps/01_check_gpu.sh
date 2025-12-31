#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export ROOT_DIR
source "${SCRIPT_DIR}/../lib/common/warnings.sh"
source "${SCRIPT_DIR}/../lib/common/log.sh"
source "${SCRIPT_DIR}/../lib/deps/venv.sh"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  log_warn "[gpu] ⚠ nvidia-smi not found; ensure this RunPod image has NVIDIA drivers."
elif ! nvidia-smi >/dev/null 2>&1; then
  log_warn "[gpu] ⚠ nvidia-smi failed; GPU may not be available."
fi

# Print CUDA/Torch ABI hint if available
venv_dir="$(get_venv_dir)"
if [ -d "${venv_dir}" ]; then
  CU_VER=$("${venv_dir}/bin/python" - <<'PY' || true
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

