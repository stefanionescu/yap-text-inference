#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "[trt] Setting environment defaults (TRT-LLM image)..."

# Source modular env configuration
source "${SCRIPT_DIR}/env/helpers.sh"
source "${SCRIPT_DIR}/env/models.sh"
source "${SCRIPT_DIR}/env/trt_config.sh"
source "${SCRIPT_DIR}/env/gpu_detect.sh"

# Validate that the baked-in engine is compatible with the runtime GPU
# This must run after gpu_detect.sh sets GPU_SM_ARCH
source "${SCRIPT_DIR}/env/validate_engine.sh"

source "${SCRIPT_DIR}/env/final_defaults.sh"

log_info "[trt] Docker TRT-LLM Configuration: GPU=${DETECTED_GPU_NAME:-unknown}"
if [ "${DEPLOY_CHAT}" = "1" ]; then
  log_info "[trt] Chat model (tokenizer): ${CHAT_MODEL:-none}"
  log_info "[trt] TRT engine repo: ${TRT_ENGINE_REPO:-none}"
fi
if [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "[trt] Tool model: ${TOOL_MODEL:-none} (classifier, not TRT)"
fi

