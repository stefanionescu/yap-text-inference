#!/usr/bin/env bash
# shellcheck disable=SC1091
# Tool-only deploy mode configuration.
#
# Sources shared deploy mode logic from common/ and sets tool-specific flags.

_DEPLOY_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find common scripts directory (works in Docker and dev contexts)
if [ -d "/app/common/scripts" ]; then
  _DEPLOY_COMMON_SCRIPTS="/app/common/scripts"
elif [ -d "${_DEPLOY_SCRIPT_DIR}/../../../common/scripts" ]; then
  _DEPLOY_COMMON_SCRIPTS="${_DEPLOY_SCRIPT_DIR}/../../../common/scripts"
else
  echo "[tool] ERROR: Cannot find common scripts directory" >&2
  exit 1
fi

# Source shared deploy mode logic
source "${_DEPLOY_COMMON_SCRIPTS}/deploy_mode.sh"

# Initialize deploy mode for tool-only (engine arg is irrelevant for tool-only)
init_deploy_mode "[tool]" "vllm"
