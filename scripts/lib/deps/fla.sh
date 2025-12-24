#!/usr/bin/env bash

# Flash Linear Attention (fla-core) dependency for Kimi models
# Required for: moonshotai/Kimi-*, cerebras/Kimi-*

FLA_CORE_PACKAGE="fla-core"

# Check if model requires fla-core (Kimi Linear models)
model_needs_fla_core() {
  local model="${1:-}"
  if [ -z "${model}" ]; then
    return 1
  fi
  
  local lowered
  if [[ -n "${BASH_VERSION:-}" && "${BASH_VERSION%%.*}" -ge 4 ]]; then
    lowered="${model,,}"
  else
    lowered="$(echo "${model}" | tr '[:upper:]' '[:lower:]')"
  fi
  
  # Match Kimi-Linear models from moonshotai or cerebras
  if [[ "${lowered}" == *"kimi-linear"* ]] || [[ "${lowered}" == *"kimi_linear"* ]]; then
    return 0
  fi
  
  # Also match just "kimi" with "linear" nearby
  if [[ "${lowered}" == *"kimi"* ]] && [[ "${lowered}" == *"linear"* ]]; then
    return 0
  fi
  
  return 1
}

# Check if fla-core is already installed
fla_core_is_installed() {
  python -c "import fla" 2>/dev/null
}

# Install fla-core if needed for the given models
ensure_fla_core_if_needed() {
  local chat_model="${CHAT_MODEL:-}"
  local tool_model="${TOOL_MODEL:-}"
  local needs_fla=0
  
  if model_needs_fla_core "${chat_model}"; then
    needs_fla=1
    log_info "[fla] Chat model '${chat_model}' requires fla-core"
  fi
  
  if model_needs_fla_core "${tool_model}"; then
    needs_fla=1
    log_info "[fla] Tool model '${tool_model}' requires fla-core"
  fi
  
  if [ "${needs_fla}" = "0" ]; then
    return 0
  fi
  
  if fla_core_is_installed; then
    log_info "[fla] fla-core already installed"
    return 0
  fi
  
  log_info "[fla] Installing fla-core for Kimi model support..."
  if pip install --no-cache-dir -U "${FLA_CORE_PACKAGE}"; then
    log_info "[fla] ✓ fla-core installed successfully"
    return 0
  else
    log_err "[fla] Failed to install fla-core"
    return 1
  fi
}

