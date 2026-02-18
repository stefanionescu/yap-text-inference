#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# GPU Availability Check
# =============================================================================
# Verifies that NVIDIA GPU drivers are available and functional.
# Logs warnings if nvidia-smi is missing or fails.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export ROOT_DIR
source "${SCRIPT_DIR}/../lib/noise/python.sh"
source "${SCRIPT_DIR}/../lib/common/log.sh"
source "${SCRIPT_DIR}/../lib/deps/venv/main.sh"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  log_warn "[gpu] ⚠ nvidia-smi not found; ensure this RunPod image has NVIDIA drivers."
elif ! nvidia-smi >/dev/null 2>&1; then
  log_warn "[gpu] ⚠ nvidia-smi failed; GPU may not be available."
fi

# Print CUDA/Torch ABI hint if available
venv_dir="$(get_venv_dir)"
if [ -d "${venv_dir}" ]; then
  CU_VER=$(PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
    "${venv_dir}/bin/python" -m src.scripts.env torch-cuda-version 2>/dev/null || true)
  if [ -n "${CU_VER:-}" ]; then
    log_info "[gpu] Torch CUDA version detected: ${CU_VER}"
  fi
fi
