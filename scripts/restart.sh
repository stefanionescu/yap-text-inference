#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Server Restart Script
# =============================================================================
# Restarts the inference server with optional model/quantization reconfiguration.
# Supports quick restart (reusing caches) or full reconfiguration with new models.
#
# Usage: bash scripts/restart.sh <deploy_mode> [options]
# See usage() below for full options.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced helpers rely on ROOT_DIR
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/lib/noise/python.sh"
source "${SCRIPT_DIR}/lib/common/log.sh"
source "${SCRIPT_DIR}/config/values/core.sh"
source "${SCRIPT_DIR}/config/patterns.sh"
source "${SCRIPT_DIR}/config/messages/restart.sh"
source "${SCRIPT_DIR}/lib/common/params.sh"
source "${SCRIPT_DIR}/lib/common/warmup.sh"
source "${SCRIPT_DIR}/lib/deps/venv/main.sh"
source "${SCRIPT_DIR}/lib/runtime/restart/main.sh"
source "${SCRIPT_DIR}/lib/runtime/pipeline.sh"
source "${SCRIPT_DIR}/lib/common/model/validate.sh"
source "${SCRIPT_DIR}/lib/common/cli.sh"
source "${SCRIPT_DIR}/lib/common/pytorch_guard.sh"
source "${SCRIPT_DIR}/lib/restart/overrides.sh"
source "${SCRIPT_DIR}/lib/restart/args.sh"
source "${SCRIPT_DIR}/lib/restart/basic.sh"
source "${SCRIPT_DIR}/lib/restart/reconfigure/run.sh"
source "${SCRIPT_DIR}/lib/restart/awq.sh"
source "${SCRIPT_DIR}/lib/restart/errors.sh"
source "${SCRIPT_DIR}/lib/env/restart.sh"
source "${SCRIPT_DIR}/lib/restart/launch.sh"
source "${SCRIPT_DIR}/lib/restart/pipeline.sh"
source "${SCRIPT_DIR}/engines/vllm/push.sh"
source "${SCRIPT_DIR}/engines/trt/push.sh"
source "${SCRIPT_DIR}/engines/trt/detect.sh"
source "${SCRIPT_DIR}/lib/common/gpu_detect.sh"
source "${SCRIPT_DIR}/lib/common/cuda.sh"

usage() {
  local line
  for line in "${CFG_RESTART_USAGE_LINES[@]}"; do
    printf '%s\n' "${line}"
  done
  exit 1
}

restart_main "$@"
