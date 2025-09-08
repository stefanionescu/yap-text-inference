#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Checking GPU availability"
if ! command -v nvidia-smi >/dev/null 2>&1; then
  log_warn "nvidia-smi not found; ensure this RunPod image has NVIDIA drivers."
else
  nvidia-smi || true
fi


