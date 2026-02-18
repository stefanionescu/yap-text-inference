#!/usr/bin/env bash
# shellcheck disable=SC1091
source "/app/common/scripts/deploy_mode.sh"

# Initialize deploy mode for vLLM
init_deploy_mode "[vllm]" "vllm"
