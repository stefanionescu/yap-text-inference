#!/usr/bin/env bash
# TRT deploy mode configuration.
#
# Sources shared deploy mode logic from common/ and sets TRT-specific flags.

_DEPLOY_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find common scripts directory (works in Docker and dev contexts)
if [ -d "/app/common/scripts" ]; then
  _DEPLOY_COMMON_SCRIPTS="/app/common/scripts"
elif [ -d "${_DEPLOY_SCRIPT_DIR}/../../../common/scripts" ]; then
  _DEPLOY_COMMON_SCRIPTS="${_DEPLOY_SCRIPT_DIR}/../../../common/scripts"
else
  echo "[trt] ERROR: Cannot find common scripts directory" >&2
  exit 1
fi

# Source shared deploy mode logic
source "${_DEPLOY_COMMON_SCRIPTS}/deploy_mode.sh"

# Initialize deploy mode for TRT
init_deploy_mode "[trt]" "trt"

