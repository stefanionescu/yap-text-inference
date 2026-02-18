#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# TRT-LLM Quantization Entry Point
# =============================================================================
# Thin entrypoint for TRT quantization/build pipeline.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced helpers rely on ROOT_DIR
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Source common utilities
source "${SCRIPT_DIR}/../lib/common/log.sh"
source "${SCRIPT_DIR}/../lib/common/gpu_detect.sh"
source "${SCRIPT_DIR}/../lib/common/model/detect.sh"
source "${SCRIPT_DIR}/../lib/common/hf.sh"

# Source TRT libraries (must come after model/detect.sh for MoE detection)
source "${SCRIPT_DIR}/../lib/env/trt.sh"
source "${SCRIPT_DIR}/../lib/trt/install.sh"
source "${SCRIPT_DIR}/../engines/trt/detect.sh"
source "${SCRIPT_DIR}/../engines/trt/quantize.sh"
source "${SCRIPT_DIR}/../engines/trt/build.sh"
source "${SCRIPT_DIR}/../engines/trt/push.sh"
source "${SCRIPT_DIR}/../lib/trt/pipeline.sh"

# Check if we should run TRT quantization.
TRT_TARGET_CHAT=0
if trt_pipeline_should_run; then
  TRT_TARGET_CHAT=1
fi
export TRT_TARGET_CHAT

# If TRT is not the target engine, exit quietly.
if [ "${TRT_TARGET_CHAT}" = "0" ]; then
  # shellcheck disable=SC2317  # intentional sourced-vs-executed return/exit behavior
  return 0 2>/dev/null || exit 0
fi

trt_pipeline_run || exit 1
