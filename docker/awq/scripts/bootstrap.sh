#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "Setting environment defaults (AWQ image)"

# Source modular env configuration
source "${SCRIPT_DIR}/env/helpers.sh"
source "${SCRIPT_DIR}/env/python_flashinfer.sh"
source "${SCRIPT_DIR}/env/awq_models.sh"
source "${SCRIPT_DIR}/env/runtime_flags.sh"
source "${SCRIPT_DIR}/env/limits.sh"
source "${SCRIPT_DIR}/env/tokens.sh"
source "${SCRIPT_DIR}/env/gpu_backend.sh"
source "${SCRIPT_DIR}/env/final_defaults.sh"

CONCURRENT_STATUS="sequential"
if [ "${CONCURRENT_MODEL_CALL:-0}" = "1" ]; then CONCURRENT_STATUS="concurrent"; fi

log_info "Docker AWQ Configuration:"
log_info "  GPU: ${DETECTED_GPU_NAME:-unknown}"
log_info "  Deploy mode: ${DEPLOY_MODELS} (chat=${DEPLOY_CHAT}, tool=${DEPLOY_TOOL})"
if [ "${DEPLOY_DUAL:-0}" = "1" ]; then
  log_info "  Dual model: ${CHAT_MODEL:-${DUAL_MODEL:-none}}"
  log_info "  Dual quantization: ${CHAT_QUANTIZATION:-${QUANTIZATION:-awq}}"
else
  log_info "  Chat model: ${CHAT_MODEL:-none}"
  log_info "  Tool model: ${TOOL_MODEL:-none}"
  log_info "  Quantization: ${QUANTIZATION:-awq}"
fi
log_info "  KV dtype: ${KV_DTYPE}"
log_info "  Model calls: ${CONCURRENT_STATUS}"


