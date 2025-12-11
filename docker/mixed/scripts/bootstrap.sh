#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "Setting environment defaults (Base image)"

# Source modular env configuration from scripts/env
source "${SCRIPT_DIR}/env/helpers.sh"
source "${SCRIPT_DIR}/env/python_flashinfer.sh"
source "${SCRIPT_DIR}/env/deploy_models.sh"
source "${SCRIPT_DIR}/env/quantization_select.sh"
source "${SCRIPT_DIR}/env/limits.sh"
source "${SCRIPT_DIR}/env/gpu_backend.sh"
source "${SCRIPT_DIR}/env/final_defaults.sh"

log_info "Docker Base Configuration: GPU=${DETECTED_GPU_NAME:-unknown}"
if [ "${DEPLOY_CHAT}" = "1" ]; then
  chat_precision="${CHAT_QUANTIZATION:-${QUANTIZATION:-fp16}}"
  log_info "Chat model: ${CHAT_MODEL:-none} (${chat_precision})"
fi
if [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "Tool model: ${TOOL_MODEL:-none} (fp32)"
fi


