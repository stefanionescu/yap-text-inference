#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "Setting environment defaults (AWQ image)"

# Source modular env configuration
source "${SCRIPT_DIR}/env/helpers.sh"
source "${SCRIPT_DIR}/env/python_flashinfer.sh"
source "${SCRIPT_DIR}/env/awq_models.sh"
source "${SCRIPT_DIR}/env/limits.sh"
source "${SCRIPT_DIR}/env/tokens.sh"
source "${SCRIPT_DIR}/env/gpu_backend.sh"
source "${SCRIPT_DIR}/env/final_defaults.sh"

log_info "Docker AWQ Configuration:"
log_info "  GPU: ${DETECTED_GPU_NAME:-unknown}"
log_info "  Deploy mode: ${DEPLOY_MODELS} (chat=${DEPLOY_CHAT}, tool=${DEPLOY_TOOL})"
log_info "  Chat model: ${CHAT_MODEL:-none}"
log_info "  Tool model: ${TOOL_MODEL:-none}"
log_info "  Quantization: ${QUANTIZATION:-awq}"
log_info "  KV dtype: ${KV_DTYPE}"


