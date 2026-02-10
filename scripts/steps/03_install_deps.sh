#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Dependency Installation
# =============================================================================
# Installs Python dependencies into the virtual environment. Handles vLLM,
# TRT-LLM engines, and tool-only mode (lightweight PyTorch + transformers).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export ROOT_DIR

LIB_DIR="${SCRIPT_DIR}/../lib"
source "${LIB_DIR}/noise/python.sh"
source "${LIB_DIR}/common/log.sh"

# Common deps
source "${LIB_DIR}/deps/certs.sh"
source "${LIB_DIR}/deps/pip.sh"
source "${LIB_DIR}/deps/venv.sh"
source "${LIB_DIR}/env/torch.sh"

# Engine and deploy mode detection
ENGINE="${INFERENCE_ENGINE:-vllm}"
ENGINE_LOWER="$(echo "${ENGINE}" | tr '[:upper:]' '[:lower:]')"
DEPLOY_MODE="${DEPLOY_MODE:-both}"

# =============================================================================
# TOOL-ONLY MODE (LIGHTWEIGHT)
# =============================================================================
# Tool-only deployments use a PyTorch classifier (no TRT-LLM or vLLM needed).
# Skip heavy engine dependencies and use minimal requirements.

if [ "${DEPLOY_MODE}" = "tool" ]; then
  export VENV_DIR="${VENV_DIR:-$(get_venv_dir)}"

  deps_export_pip
  ensure_ca_certificates
  export_ca_bundle_env_vars
  ensure_torch_cuda_arch_list
  ensure_virtualenv || exit 1
  ensure_pip_in_venv || exit 1
  activate_venv "${VENV_DIR}" || exit 1

  # Install lightweight tool-only requirements
  # Apply tool noise filter unless SHOW_TOOL_LOGS is enabled
  log_info "[deps] Installing tool-only requirements..."
  if [ "${SHOW_TOOL_LOGS:-0}" = "1" ]; then
    pip install --no-cache-dir -r "${ROOT_DIR}/requirements-tool.txt" || {
      log_err "[deps] ✗ Failed to install tool-only requirements"
      exit 1
    }
  else
    PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
      python -m src.scripts.filters.tool configure-logging 2>/dev/null || true
    pip install --no-cache-dir -r "${ROOT_DIR}/requirements-tool.txt" 2>&1 |
      PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
        python -m src.scripts.filters.tool filter-logs || {
      log_err "[deps] ✗ Failed to install tool-only requirements"
      exit 1
    }
  fi

  log_info "[deps] ✓ Tool-only dependencies installed"
  exit 0
fi

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

  export_env

  if ! trt_assert_cuda13_driver "deps"; then
    log_err "[cuda] ✗ CUDA 13.x required for TensorRT-LLM"
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
  log_warn "[deps] ⚠ System deps installation failed, continuing"
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

record_requirements_hash
