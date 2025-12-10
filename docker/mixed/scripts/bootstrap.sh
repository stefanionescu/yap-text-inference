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

log_info "Docker Base Configuration:"
log_info "  GPU: ${DETECTED_GPU_NAME:-unknown}"
log_info "  Deploy mode: ${DEPLOY_MODELS} (chat=${DEPLOY_CHAT}, tool=${DEPLOY_TOOL})"
log_info "  Chat model: ${CHAT_MODEL:-none}"
log_info "  Tool model: ${TOOL_MODEL:-none}"
log_info "  Quantization: ${QUANTIZATION} (chat=${CHAT_QUANTIZATION:-auto}, tool=${TOOL_QUANTIZATION:-auto})"
log_info "  KV dtype: ${KV_DTYPE}"


