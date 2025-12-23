#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export ROOT_DIR
source "${SCRIPT_DIR}/../lib/common/log.sh"

# Shared library functions
LIB_DIR="${SCRIPT_DIR}/../lib"
source "${LIB_DIR}/deps/certs.sh"
source "${LIB_DIR}/deps/trt.sh"
source "${LIB_DIR}/env/torch.sh"
source "${LIB_DIR}/env/trt.sh"  # TRT version config including TRT_PYTORCH_* variables
source "${LIB_DIR}/deps/venv.sh"
source "${LIB_DIR}/deps/reqs.sh"
source "${LIB_DIR}/deps/check.sh"
source "${SCRIPT_DIR}/../engines/trt/detect.sh"

# Engine-specific install functions
if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ] || [ "${INFERENCE_ENGINE:-vllm}" = "TRT" ]; then
  # Export TRT environment variables (TRT_PYTORCH_VERSION, etc.) for install.sh to use
  trt_export_env
  source "${SCRIPT_DIR}/../engines/trt/install.sh"
  # Validate CUDA 13.x before installing TRT dependencies
  if ! trt_assert_cuda13_driver "deps"; then
    log_err "[cuda] CUDA 13.x required for TensorRT-LLM"
    exit 1
  fi
else
  source "${SCRIPT_DIR}/../engines/vllm/install.sh"
fi

export VENV_DIR="${VENV_DIR:-$(get_venv_dir)}"

log_info "[deps] Installing Python dependencies (engine: ${INFERENCE_ENGINE:-vllm})"

export PIP_ROOT_USER_ACTION=${PIP_ROOT_USER_ACTION:-ignore}
export PIP_DISABLE_PIP_VERSION_CHECK=${PIP_DISABLE_PIP_VERSION_CHECK:-1}
export PIP_NO_INPUT=${PIP_NO_INPUT:-1}
export PIP_PREFER_BINARY=${PIP_PREFER_BINARY:-1}
# Prefer AOT kernels for FlashInfer to avoid long first-run JIT compiles
export FLASHINFER_ENABLE_AOT=${FLASHINFER_ENABLE_AOT:-1}

# Ensure CA certificates and export CA bundle environment
ensure_ca_certificates
export_ca_bundle_env_vars

# Install system-level dependencies (MPI for TRT, etc.)
ensure_trt_system_deps || {
  log_warn "[deps] System deps installation failed, continuing (may fail later if mpi4py needed)"
}

# Ensure correct CUDA arch is visible during build steps (FlashInfer, etc.)
ensure_torch_cuda_arch_list

ensure_virtualenv || exit 1

ensure_pip_in_venv || exit 1

# Activate venv so pip/python commands use venv versions
activate_venv "${VENV_DIR}" || exit 1

# Check existing dependency versions (sets NEEDS_* globals)
check_trt_deps_status "${VENV_DIR}" "${TRT_PYTORCH_VERSION%%+*}" "${TRT_TORCHVISION_VERSION%%+*}" "${TRT_VERSION:-1.2.0rc5}" "requirements-trt.txt" || true

# Engine-specific installation
if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ] || [ "${INFERENCE_ENGINE:-vllm}" = "TRT" ]; then
  # Install only what is missing/wrong, keep order but skip satisfied steps
  if [[ "${NEEDS_PYTORCH}" = "1" || "${NEEDS_TORCHVISION}" = "1" ]]; then
    trt_install_pytorch || {
      log_err "[trt] PyTorch installation failed"
      exit 1
    }
  else
    log_info "[trt] PyTorch/TorchVision already correct; skipping"
  fi
  
  if [[ "${NEEDS_REQUIREMENTS}" = "1" ]]; then
    filter_requirements_without_flashinfer
    install_requirements_without_flashinfer
  else
    log_info "[trt] requirements-trt already satisfied; skipping"
  fi
  
  if [[ "${NEEDS_TRTLLM}" = "1" ]]; then
    trt_install_tensorrt_llm || {
      log_err "[trt] TensorRT-LLM installation failed"
      exit 1
    }
  else
    log_info "[trt] TensorRT-LLM already correct; skipping"
  fi
  
  # Validate and prepare repo
  trt_validate_installation || {
    log_err "[trt] TensorRT-LLM validation failed"
    exit 1
  }
  
  trt_prepare_repo || {
    log_err "[trt] TensorRT-LLM repo preparation failed"
    exit 1
  }
  
  log_info "[trt] ✓ TensorRT-LLM installation complete"
else
  # vLLM installation path
  filter_requirements_without_flashinfer
  install_requirements_without_flashinfer
  install_llmcompressor_without_deps
  
  vllm_install_flashinfer
fi

record_requirements_hash
