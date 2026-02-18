#!/usr/bin/env bash
# =============================================================================
# CUDA Guard Utilities
# =============================================================================
# Validates CUDA driver requirements for TensorRT-LLM (CUDA 13.x).
# Ensures validation runs exactly once per deployment.

_CUDA_GUARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/core.sh
source "${_CUDA_GUARD_DIR}/../../config/values/core.sh"
# shellcheck source=../../config/patterns.sh
source "${_CUDA_GUARD_DIR}/../../config/patterns.sh"

ensure_cuda_ready_for_engine() {
  local phase="${1:-engine}"
  local engine="${INFERENCE_ENGINE:-${CFG_DEFAULT_ENGINE}}"
  local deploy_mode="${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}"

  # Tool-only mode uses plain PyTorch tool model, no TRT/vLLM engine needed
  if [ "${deploy_mode}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    return 0
  fi

  case "${engine,,}" in
    "${CFG_ENGINE_TRT}")
      if ! trt_assert_cuda13_driver "${phase}"; then
        log_err "[${phase}] ✗ CUDA 13.x required for TensorRT-LLM"
        return 1
      fi
      ;;
  esac

  return 0
}
