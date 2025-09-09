#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Wiping runtime: stopping server, freeing GPU, clearing caches"
HARD_RESET="${HARD_RESET:-0}" bash "${SCRIPT_DIR}/stop.sh"

log_info "Post-wipe GPU owners:"
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi --query-compute-apps=pid,process_name,used_gpu_memory --format=csv || true
else
  log_warn "nvidia-smi not found"
fi


