#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "[vllm] Setting environment defaults (vLLM AWQ image)"

# Source modular env configuration
source "${SCRIPT_DIR}/env/helpers.sh"
source "${SCRIPT_DIR}/env/python_flashinfer.sh"
source "${SCRIPT_DIR}/env/awq_models.sh"
source "${SCRIPT_DIR}/env/limits.sh"
source "${SCRIPT_DIR}/env/tokens.sh"
source "${SCRIPT_DIR}/env/gpu_backend.sh"
source "${SCRIPT_DIR}/env/final_defaults.sh"

log_info "[vllm] Docker vLLM Configuration: GPU=${DETECTED_GPU_NAME:-unknown}"
if [ "${DEPLOY_CHAT}" = "1" ]; then
  log_info "[vllm] Chat model: ${CHAT_MODEL:-none} (${QUANTIZATION:-awq})"
fi
if [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "[vllm] Tool model: ${TOOL_MODEL:-none} (fp32)"
fi

