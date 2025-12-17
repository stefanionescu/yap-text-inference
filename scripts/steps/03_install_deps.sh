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
source "${LIB_DIR}/deps/venv.sh"
source "${LIB_DIR}/deps/reqs.sh"
source "${SCRIPT_DIR}/../engines/trt/detect.sh"

# Engine-specific install functions
if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ] || [ "${INFERENCE_ENGINE:-vllm}" = "TRT" ]; then
  source "${SCRIPT_DIR}/../engines/trt/install.sh"
  # Validate CUDA 13.x before installing TRT dependencies
  if ! trt_assert_cuda13_driver "install_deps"; then
    log_err "Aborting: CUDA 13.x required for TensorRT-LLM"
    exit 1
  fi
else
  source "${SCRIPT_DIR}/../engines/vllm/install.sh"
fi

log_info "Installing Python dependencies (engine: ${INFERENCE_ENGINE:-vllm})"

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
  log_warn "System deps installation failed, continuing (may fail later if mpi4py needed)"
}

# Ensure correct CUDA arch is visible during build steps (FlashInfer, etc.)
ensure_torch_cuda_arch_list

ensure_virtualenv || exit 1

ensure_pip_in_venv || exit 1

# Engine-specific installation
if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ] || [ "${INFERENCE_ENGINE:-vllm}" = "TRT" ]; then
  # Install app requirements first (before TRT-LLM to avoid conflicts)
  filter_requirements_without_flashinfer
  install_requirements_without_flashinfer
  
  # Run full TRT-LLM installation (PyTorch -> TRT-LLM -> validate -> clone repo)
  trt_full_install || {
    log_err "TensorRT-LLM installation failed"
    exit 1
  }
else
  # vLLM installation path
  filter_requirements_without_flashinfer
  install_requirements_without_flashinfer
  install_llmcompressor_without_deps
  
  vllm_install_flashinfer
fi

record_requirements_hash
