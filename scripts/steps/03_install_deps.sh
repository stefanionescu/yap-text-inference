#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/../lib/log.sh"

# Shared library functions
LIB_DIR="${SCRIPT_DIR}/../lib"
source "${LIB_DIR}/certs.sh"
source "${LIB_DIR}/torch_env.sh"
source "${LIB_DIR}/venv.sh"
source "${LIB_DIR}/reqs.sh"
source "${LIB_DIR}/flashinfer.sh"

log_info "Installing Python dependencies"

export PIP_ROOT_USER_ACTION=${PIP_ROOT_USER_ACTION:-ignore}
export PIP_DISABLE_PIP_VERSION_CHECK=${PIP_DISABLE_PIP_VERSION_CHECK:-1}
export PIP_NO_INPUT=${PIP_NO_INPUT:-1}
export PIP_PREFER_BINARY=${PIP_PREFER_BINARY:-1}
# Prefer AOT kernels for FlashInfer to avoid long first-run JIT compiles
export FLASHINFER_ENABLE_AOT=${FLASHINFER_ENABLE_AOT:-1}

# Ensure CA certificates and export CA bundle environment
ensure_ca_certificates
export_ca_bundle_env_vars

# Ensure correct CUDA arch is visible during build steps (FlashInfer, etc.)
ensure_torch_cuda_arch_list

ensure_virtualenv || exit 1

ensure_pip_in_venv || exit 1

filter_requirements_without_flashinfer
install_requirements_without_flashinfer

install_flashinfer_if_applicable

record_requirements_hash
