#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "[vllm] Setting environment defaults (vLLM AWQ image)..."

# Source modular env configuration
source "${SCRIPT_DIR}/env/runtime.sh"
source "${SCRIPT_DIR}/env/deploy.sh"
source "${SCRIPT_DIR}/env/gpu.sh"
source "${SCRIPT_DIR}/env/defaults.sh"

log_info "[vllm] Docker vLLM Configuration: GPU=${DETECTED_GPU_NAME:-unknown}"
if [ "${DEPLOY_CHAT}" = "1" ]; then
  # Quantization is auto-detected from CHAT_MODEL name by Python (src/config/engine.py)
  log_info "[vllm] Chat model: ${CHAT_MODEL:-none} (quant: ${CHAT_QUANTIZATION:-auto})"
fi
if [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "[vllm] Tool model: ${TOOL_MODEL:-none} (fp32)"
fi

