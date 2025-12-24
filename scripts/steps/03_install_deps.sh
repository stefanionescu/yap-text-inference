#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export ROOT_DIR

LIB_DIR="${SCRIPT_DIR}/../lib"
source "${LIB_DIR}/common/log.sh"

# Common deps
source "${LIB_DIR}/deps/certs.sh"
source "${LIB_DIR}/deps/pip.sh"
source "${LIB_DIR}/deps/venv.sh"
source "${LIB_DIR}/deps/fla.sh"
source "${LIB_DIR}/env/torch.sh"

# Engine detection
ENGINE="${INFERENCE_ENGINE:-vllm}"
ENGINE_LOWER="$(echo "${ENGINE}" | tr '[:upper:]' '[:lower:]')"

log_info "[deps] Installing dependencies for engine: ${ENGINE}"

# =============================================================================
# ENGINE-SPECIFIC SETUP
# =============================================================================

# Source reqs.sh for record_requirements_hash (used by both engines)
source "${LIB_DIR}/deps/reqs.sh"

if [ "${ENGINE_LOWER}" = "trt" ]; then
  # TRT requires CUDA 13.x validation and specific env vars
  source "${LIB_DIR}/env/trt.sh"
  source "${LIB_DIR}/deps/trt.sh"
  source "${LIB_DIR}/deps/check.sh"
  source "${SCRIPT_DIR}/../engines/trt/detect.sh"
  source "${SCRIPT_DIR}/../engines/trt/install.sh"
  
  trt_export_env
  
  if ! trt_assert_cuda13_driver "deps"; then
    log_err "[cuda] CUDA 13.x required for TensorRT-LLM"
    exit 1
  fi
else
  # vLLM - also sources trt.sh for ensure_trt_system_deps (no-op for vLLM)
  source "${LIB_DIR}/deps/trt.sh"
  source "${LIB_DIR}/deps/vllm.sh"
fi

# =============================================================================
# COMMON SETUP
# =============================================================================

export VENV_DIR="${VENV_DIR:-$(get_venv_dir)}"

deps_export_pip
ensure_ca_certificates
export_ca_bundle_env_vars

# System deps (MPI for TRT - no-op for vLLM)
ensure_trt_system_deps || {
  log_warn "[deps] System deps installation failed, continuing"
}

ensure_torch_cuda_arch_list
ensure_virtualenv || exit 1
ensure_pip_in_venv || exit 1
activate_venv "${VENV_DIR}" || exit 1

# =============================================================================
# ENGINE-SPECIFIC INSTALLATION
# =============================================================================

if [ "${ENGINE_LOWER}" = "trt" ]; then
  trt_install_deps "${VENV_DIR}" || exit 1
else
  vllm_install_deps || exit 1
fi

# Model-specific dependencies (e.g., fla-core for Kimi models)
ensure_fla_core_if_needed || exit 1

record_requirements_hash
