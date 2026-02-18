#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# TRT-LLM Python Dependency Helpers
# =============================================================================

_TRT_PYDEPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=../../lib/deps/pip.sh
source "${_TRT_PYDEPS_DIR}/../deps/pip.sh"
# shellcheck source=../env/trt.sh
source "${_TRT_PYDEPS_DIR}/../env/trt.sh"

# Ensure CUDA_HOME is set and valid
trt_ensure_cuda_home() {
  if [ -z "${CUDA_HOME:-}" ]; then
    if [ -d "/usr/local/cuda" ]; then
      export CUDA_HOME="/usr/local/cuda"
    elif [ -d "/usr/local/cuda-13.0" ]; then
      export CUDA_HOME="/usr/local/cuda-13.0"
    else
      log_err "[trt] ✗ CUDA_HOME is not set. Install CUDA Toolkit 13.x and export CUDA_HOME."
      return 1
    fi
  fi

  if [ ! -d "${CUDA_HOME}/lib64" ]; then
    log_err "[trt] ✗ CUDA_HOME/lib64 not found: ${CUDA_HOME}/lib64"
    return 1
  fi

  # Check for CUDA 13 libraries (required by TRT-LLM 1.2.0rc5)
  if ! find "${CUDA_HOME}/lib64" -maxdepth 1 -name "libcublasLt.so.13*" 2>/dev/null | grep -q '.'; then
    if ! ldconfig -p 2>/dev/null | grep -q "libcublasLt.so.13"; then
      log_warn "[trt] ⚠ libcublasLt.so.13 not found - TensorRT-LLM 1.2.0rc5 requires CUDA 13.x runtime libraries"
    fi
  fi

  # Ensure CUDA libs are in LD_LIBRARY_PATH
  case ":${LD_LIBRARY_PATH:-}:" in
    *":${CUDA_HOME}/lib64:"*) ;;
    *) export LD_LIBRARY_PATH="${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}" ;;
  esac

  return 0
}

# Install PyTorch and TorchVision with matching CUDA versions
# MUST be done BEFORE TensorRT-LLM to prevent version conflicts
trt_install_pytorch() {
  local torch_version="${TRT_PYTORCH_VERSION:-${CFG_TRT_PYTORCH_VERSION}}"
  local torchvision_version="${TRT_TORCHVISION_VERSION:-${CFG_TRT_TORCHVISION_VERSION}}"
  local torch_idx="${TRT_PYTORCH_INDEX_URL:-${CFG_TRT_PYTORCH_INDEX_URL}}"

  log_section "[trt] Installing PyTorch..."

  # Install torch and torchvision together from the SAME index to ensure CUDA version match
  local pip_cmd=(
    install --no-cache-dir
    --index-url "${torch_idx}"
    "torch==${torch_version}"
    "torchvision==${torchvision_version}"
  )

  _trt_pip_install_with_retry "${pip_cmd[@]}" || {
    log_err "[trt] ✗ Failed to install PyTorch"
    return 1
  }

  return 0
}

# Persist torch/torchvision pins so downstream pip installs cannot swap CUDA builds
trt_write_torch_constraints_file() {
  local constraints_file="${TRT_TORCH_CONSTRAINTS_FILE:-${ROOT_DIR:-.}/${CFG_TRT_TORCH_CONSTRAINTS_REL}}"
  local torch_version="${TRT_PYTORCH_VERSION:-${CFG_TRT_PYTORCH_VERSION}}"
  local torchvision_version="${TRT_TORCHVISION_VERSION:-${CFG_TRT_TORCHVISION_VERSION}}"

  mkdir -p "$(dirname "${constraints_file}")"
  cat >"${constraints_file}" <<EOF
torch==${torch_version}
torchvision==${torchvision_version}
EOF

  echo "${constraints_file}"
}

# pip install with retry
_trt_pip_install_with_retry() {
  local max_attempts="${PIP_INSTALL_ATTEMPTS:-${CFG_PIP_INSTALL_ATTEMPTS}}"
  local delay="${PIP_INSTALL_BACKOFF_SECONDS:-${CFG_PIP_INSTALL_BACKOFF_SECONDS}}"
  local attempt=1

  while [ "${attempt}" -le "${max_attempts}" ]; do
    if pip_quiet "$@"; then
      return 0
    fi
    attempt=$((attempt + 1))
    if [ "${attempt}" -le "${max_attempts}" ]; then
      log_warn "[trt] ⚠ pip attempt failed; retrying after ${delay}s..."
      sleep "${delay}"
      delay=$((delay * 2))
    fi
  done

  log_err "[trt] ✗ pip command failed after ${max_attempts} attempts"
  return 1
}

# Install TensorRT-LLM from NVIDIA PyPI
trt_install_tensorrt_llm() {
  local nvidia_index="${TRT_EXTRA_INDEX_URL}"
  local target="${TRT_PIP_SPEC}"
  local trt_no_deps="${TRTLLM_NO_DEPS:-0}"
  local torch_idx="${TRT_PYTORCH_INDEX_URL:-${CFG_TRT_PYTORCH_INDEX_URL}}"
  local constraints_file
  constraints_file=$(trt_write_torch_constraints_file) || {
    log_err "[trt] ✗ Unable to materialize torch constraints"
    return 1
  }

  log_info "[trt] Installing the TRT wheel..."

  # NOTE: Do NOT use --upgrade here - it can replace torch with a different CUDA version
  local pip_cmd=(
    install --no-cache-dir --timeout 120 --retries 20
    --index-url "${nvidia_index}"
    --extra-index-url "https://pypi.org/simple"
    --extra-index-url "${torch_idx}"
  )
  if [ "${trt_no_deps}" = "1" ]; then
    pip_cmd+=(--no-deps)
  fi
  if [ -n "${constraints_file}" ] && [ -f "${constraints_file}" ]; then
    pip_cmd+=(--constraint "${constraints_file}")
  fi
  pip_cmd+=("${target}")

  _trt_pip_install_with_retry "${pip_cmd[@]}" || {
    log_err "[trt] ✗ Failed to install the TRT wheel"
    return 1
  }

  return 0
}
