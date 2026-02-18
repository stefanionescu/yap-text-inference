#!/usr/bin/env bash
# =============================================================================
# Early Model Validation
# =============================================================================
# Validates models against allowlists before deployment starts.
# Calls Python to check models without loading heavy vLLM dependencies.

validate_models_early() {
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/scripts/config/values/core.sh"

  # Find Python - prefer venv if available
  local python_cmd="python3"
  if [ -f "${ROOT_DIR}/.venv/bin/python" ]; then
    python_cmd="${ROOT_DIR}/.venv/bin/python"
  fi

  # Run lightweight validation via Python module
  # Environment variables are read directly by the Python script
  if ! PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
    DEPLOY_MODE="${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}" \
    CHAT_MODEL="${CHAT_MODEL:-}" \
    TOOL_MODEL="${TOOL_MODEL:-}" \
    CHAT_QUANTIZATION="${CHAT_QUANTIZATION:-}" \
    INFERENCE_ENGINE="${INFERENCE_ENGINE:-${CFG_DEFAULT_ENGINE}}" \
    "${python_cmd}" -m src.scripts.validate; then
    log_err "[validate] ✗ Model validation failed - check model names and allowlists"
    return 1
  fi
  return 0
}
