#!/usr/bin/env bash
# =============================================================================
# CUDA Guard Utilities
# =============================================================================
# Validates CUDA driver requirements for TensorRT-LLM (CUDA 13.x).
# Ensures validation runs exactly once per deployment.

ensure_cuda_ready_for_engine() {
  local phase="${1:-engine}"
  local engine="${INFERENCE_ENGINE:-trt}"

  case "${engine,,}" in
    trt)
      if ! trt_assert_cuda13_driver "${phase}"; then
        log_err "[${phase}] ✗ CUDA 13.x required for TensorRT-LLM"
        return 1
      fi
      ;;
  esac

  return 0
}


