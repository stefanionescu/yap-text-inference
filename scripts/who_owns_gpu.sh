#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

if ! command -v nvidia-smi >/dev/null 2>&1; then
  log_warn "nvidia-smi not found; no NVIDIA GPU or drivers missing"
  exit 0
fi

log_info "GPU compute owners (pid, process, used_gpu_memory):"
nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv || true


