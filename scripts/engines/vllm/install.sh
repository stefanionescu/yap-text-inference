#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# vLLM Installation Utilities
# =============================================================================
# FlashInfer and vLLM-specific dependency installation.

_VLLM_INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_VLLM_INSTALL_DIR}/detect.sh"
source "${_VLLM_INSTALL_DIR}/../../lib/env/flashinfer.sh"
source "${_VLLM_INSTALL_DIR}/../../lib/deps/venv/main.sh"

# Validate vLLM installation
vllm_validate_installation() {
  local python_exec
  python_exec="$(get_venv_python)"

  if [ ! -x "${python_exec}" ]; then
    log_err "[vllm] ✗ No venv Python found"
    return 1
  fi

  log_info "[vllm] Validating vLLM installation..."

  if ! vllm_is_installed "${python_exec}"; then
    log_err "[vllm] ✗ vLLM not installed or not importable"
    return 1
  fi

  local vllm_ver
  vllm_ver="$(vllm_get_version "${python_exec}")"
  log_info "[vllm] vLLM version: ${vllm_ver}"

  if flashinfer_present_py "${python_exec}"; then
    log_info "[vllm] FlashInfer: available"
    export HAS_FLASHINFER=1
  else
    log_info "[vllm] FlashInfer: not available (using XFORMERS)"
    export HAS_FLASHINFER=0
  fi

  return 0
}
