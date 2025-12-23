#!/usr/bin/env bash
# =============================================================================
# vLLM Dependency Installation
# =============================================================================
# Single entry point for vLLM dependency installation.

_VLLM_DEPS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source vLLM-specific modules
source "${_VLLM_DEPS_DIR}/../../engines/vllm/install.sh"
source "${_VLLM_DEPS_DIR}/reqs.sh"

# Main entry point for vLLM dependency installation
# Call this after venv is set up and activated
vllm_install_deps() {
  log_info "[vllm] Installing vLLM dependencies..."
  
  filter_requirements_without_flashinfer || return 1
  install_requirements_without_flashinfer || return 1
  install_llmcompressor_without_deps || return 1
  vllm_install_flashinfer
  
  log_info "[vllm] ✓ vLLM dependencies installed"
  return 0
}

