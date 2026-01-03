#!/usr/bin/env bash
# TRT deploy mode configuration.
#
# Sources shared deploy mode logic from common/ and adds TRT-specific logging.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find common scripts directory (works in Docker and dev contexts)
if [ -d "/app/common/scripts" ]; then
  COMMON_SCRIPTS="/app/common/scripts"
elif [ -d "${SCRIPT_DIR}/../../../common/scripts" ]; then
  COMMON_SCRIPTS="${SCRIPT_DIR}/../../../common/scripts"
else
  echo "[trt] ERROR: Cannot find common scripts directory" >&2
  exit 1
fi

# Source shared deploy mode logic
source "${COMMON_SCRIPTS}/deploy_mode.sh"

# Initialize deploy mode for TRT
init_deploy_mode "[trt]" "trt"

# Log configured models for TRT
if [ "${DEPLOY_CHAT}" = "1" ] || [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "[trt] Configured models:"
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    log_info "[trt]   Chat (tokenizer): ${CHAT_MODEL}"
    log_info "[trt]   TRT engine repo: ${TRT_ENGINE_REPO:-<mount required>}"
  fi
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    log_info "[trt]   Tool classifier: ${TOOL_MODEL}"
  fi
fi
