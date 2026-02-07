#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "[trt] Setting environment defaults..."

# Source modular env configuration
source "${SCRIPT_DIR}/env/deploy.sh"
source "${SCRIPT_DIR}/env/trt.sh"
source "${SCRIPT_DIR}/env/gpu.sh"

# Validate that the baked-in engine is compatible with the runtime GPU
# This must run after gpu.sh sets GPU_SM_ARCH
source "${SCRIPT_DIR}/validate_engine.sh"

source "${SCRIPT_DIR}/env/defaults.sh"

if [ "${DEPLOY_CHAT}" = "1" ]; then
  log_info "[trt] Chat model: ${TRT_ENGINE_REPO:-none}"
fi
if [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "[trt] Tool model: ${TOOL_MODEL:-none}"
fi
