#!/usr/bin/env bash
# vLLM deploy mode and quantization configuration.
#
# Sources shared deploy mode logic from common/ and sets vLLM-specific defaults.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find common scripts directory (works in Docker and dev contexts)
if [ -d "/app/common/scripts" ]; then
  COMMON_SCRIPTS="/app/common/scripts"
elif [ -d "${SCRIPT_DIR}/../../../common/scripts" ]; then
  COMMON_SCRIPTS="${SCRIPT_DIR}/../../../common/scripts"
else
  echo "[vllm] ERROR: Cannot find common scripts directory" >&2
  exit 1
fi

# Source shared deploy mode logic
source "${COMMON_SCRIPTS}/deploy_mode.sh"

# Initialize deploy mode for vLLM
init_deploy_mode "[vllm]" "vllm"

# Set quantization for chat model (vLLM defaults to awq for pre-quantized models)
if [ "${DEPLOY_CHAT}" = "1" ]; then
  export CHAT_QUANTIZATION="${CHAT_QUANTIZATION:-awq}"
fi
