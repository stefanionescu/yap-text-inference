#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "[tool] Setting environment defaults (tool-only image)..."

# Source modular env configuration (no runtime.sh or gpu.sh -- tool-only doesn't need them)
source "${SCRIPT_DIR}/env/deploy.sh"
source "${SCRIPT_DIR}/env/defaults.sh"

if [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "[tool] Tool model: ${TOOL_MODEL:-none}"
fi
