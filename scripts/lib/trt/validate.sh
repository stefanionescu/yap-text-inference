#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Validation Helpers
# =============================================================================

_TRT_VALIDATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_trt_validation_root() {
  echo "${ROOT_DIR:-$(cd "${_TRT_VALIDATE_DIR}/../../.." && pwd)}"
}

# Validate Python shared library
trt_validate_python_libraries() {
  log_info "[trt] Checking Python shared library..."
  local python_root
  python_root="$(_trt_validation_root)"
  if ! PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
    python -W ignore::RuntimeWarning -m src.scripts.trt.validation python-libs; then
    return 1
  fi
}

# Validate CUDA runtime
trt_validate_cuda_runtime() {
  log_info "[trt] Checking CUDA Python bindings..."
  local python_root
  python_root="$(_trt_validation_root)"
  if ! PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
    python -W ignore::RuntimeWarning -m src.scripts.trt.validation cuda-runtime 2>&1; then
    log_err "[trt] ✗ CUDA Python bindings not working"
    log_err "[trt] ✗ Hint: Ensure cuda-python>=13.0 and that CUDA_HOME/lib64 contains CUDA 13 runtime libraries"
    return 1
  fi
  log_info "[trt] ✓ CUDA bindings OK"
  return 0
}

# Validate MPI runtime
trt_validate_mpi_runtime() {
  local need_mpi="${NEED_MPI:-0}"

  if [ "${need_mpi}" = "1" ]; then
    log_info "[trt] Checking MPI runtime..."
    local python_root
    python_root="$(_trt_validation_root)"
    PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
      python -W ignore::RuntimeWarning -m src.scripts.trt.validation mpi
  else
    log_info "[trt] Skipping MPI check (NEED_MPI=0)"
  fi
}

# Validate TensorRT-LLM installation
trt_validate_installation() {
  log_blank
  log_info "[trt] Validating TRT wheel installation..."

  local python_root
  python_root="$(_trt_validation_root)"
  local trt_output
  trt_output=$(PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
    python -W ignore::RuntimeWarning -m src.scripts.trt.validation trt-install 2>&1) || {
    log_err "[trt] ✗ TensorRT-LLM not installed or not importable"
    echo "${trt_output}" >&2
    return 1
  }
  if [[ ${trt_output} == *"MODELOPT_MISSING"* ]]; then
    log_warn "[trt] ⚠ TensorRT-LLM import reported: ${trt_output} (ignored for modelopt)"
  else
    log_info "${trt_output}"
  fi

  trt_validate_python_libraries || return 1
  trt_validate_cuda_runtime || return 1
  trt_validate_mpi_runtime || return 1

  if ! command -v trtllm-build >/dev/null 2>&1; then
    log_warn "[trt] ⚠ trtllm-build command not found in PATH"
  fi

  log_blank
  return 0
}

