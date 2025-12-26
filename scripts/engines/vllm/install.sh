#!/usr/bin/env bash
# =============================================================================
# vLLM Installation Utilities
# =============================================================================
# FlashInfer and vLLM-specific dependency installation.

_VLLM_INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_VLLM_INSTALL_DIR}/detect.sh"
source "${_VLLM_INSTALL_DIR}/../../lib/env/flashinfer.sh"

# Install FlashInfer if applicable
vllm_install_flashinfer() {
  if [ "$(uname -s)" != "Linux" ]; then
    log_warn "[vllm] ⚠ Non-Linux platform detected; skipping FlashInfer GPU wheel install."
    return 0
  fi

  local skip=${SKIP_FLASHINFER:-0}
  if [ "${skip}" = "1" ]; then
    log_info "[vllm] Skipping FlashInfer install due to configuration"
    return 0
  fi

  local python_exec="${ROOT_DIR}/.venv/bin/python"
  local cuda_ver
  local torch_ver
  
  cuda_ver="$(vllm_detect_cuda_version "${python_exec}")"
  torch_ver="$(vllm_detect_torch_version "${python_exec}")"

  if [ -n "${cuda_ver:-}" ] && [ -n "${torch_ver:-}" ]; then
    local fi_index="https://flashinfer.ai/whl/cu${cuda_ver}/torch${torch_ver}"
    local fi_pkg="flashinfer-python${FLASHINFER_VERSION_SPEC:-==0.5.3}"
    
    log_info "[vllm] Installing ${fi_pkg} (extra-index: ${fi_index})"
    if ! "${ROOT_DIR}/.venv/bin/pip" install --prefer-binary --extra-index-url "${fi_index}" "${fi_pkg}"; then
      log_warn "[vllm] ⚠ FlashInfer install failed with extra index; falling back to PyPI only"
      if ! "${ROOT_DIR}/.venv/bin/pip" install --prefer-binary "${fi_pkg}"; then
        log_warn "[vllm] ⚠ FlashInfer NOT installed. Will fall back to XFORMERS at runtime."
      fi
    fi
    log_info "[vllm] FlashInfer wheel source: ${fi_index} (CUDA=${cuda_ver} Torch=${torch_ver})"
  else
    log_warn "[vllm] ⚠ Torch/CUDA not detected; skipping FlashInfer install (will fall back to XFORMERS)."
  fi
}

# Validate vLLM installation
vllm_validate_installation() {
  local python_exec="${ROOT_DIR}/.venv/bin/python"
  
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

