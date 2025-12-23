#!/usr/bin/env bash

# Shared CUDA guard utilities.
# Ensures TRT-specific CUDA 13.x requirements are validated exactly once.

ensure_cuda_ready_for_engine() {
  local phase="${1:-engine}"
  local engine="${INFERENCE_ENGINE:-trt}"

  case "${engine,,}" in
    trt)
      if ! trt_assert_cuda13_driver "${phase}"; then
        log_err "[${phase}] CUDA 13.x required for TensorRT-LLM"
        return 1
      fi
      ;;
  esac

  return 0
}


