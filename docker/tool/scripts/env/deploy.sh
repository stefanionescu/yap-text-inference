#!/usr/bin/env bash
# shellcheck disable=SC1091
source "/app/common/scripts/deploy_mode.sh"

# Initialize deploy mode for tool-only (engine arg is irrelevant for tool-only)
init_deploy_mode "[tool]" "vllm"
