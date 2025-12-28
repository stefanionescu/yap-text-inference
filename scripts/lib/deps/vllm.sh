#!/usr/bin/env bash
# =============================================================================
# vLLM Dependency Installation
# =============================================================================
# Single entry point for vLLM dependency installation.

_VLLM_DEPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source vLLM-specific modules
source "${_VLLM_DEPS_DIR}/../../engines/vllm/install.sh"
source "${_VLLM_DEPS_DIR}/reqs.sh"

_vllm_install_quant_env() {
  local req_file
  req_file="$(get_quant_requirements_file)"
  if [ -z "${req_file}" ] || [ ! -f "${req_file}" ]; then
    log_info "[vllm] No AWQ quantization requirements found; skipping quant env install"
    return 0
  fi

  local quant_venv
  quant_venv="$(get_quant_venv_dir)"
  local quant_python
  quant_python="$(get_quant_python_binary)" || return 1

  log_info "[vllm] Preparing AWQ quantization environment at ${quant_venv} (python=${quant_python})"
  ensure_virtualenv "${quant_venv}" "${quant_python}" || return 1
  ensure_pip_in_venv "${quant_venv}" || return 1
  install_quant_requirements "${quant_venv}" "${req_file}" || return 1
  log_info "[vllm] ✓ Quantization virtualenv ready (${quant_venv})"
}

# Main entry point for vLLM dependency installation
# Call this after venv is set up and activated
vllm_install_deps() {
  log_info "[vllm] Installing vLLM dependencies..."
  
  filter_requirements_without_flashinfer || return 1
  install_requirements_without_flashinfer || return 1
  vllm_install_flashinfer
  _vllm_install_quant_env || return 1
  
  log_info "[vllm] ✓ vLLM dependencies installed"
  return 0
}
