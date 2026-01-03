#!/usr/bin/env bash
# =============================================================================
# Early Model Validation
# =============================================================================
# Validates models against allowlists before deployment starts.
# Calls Python to check models without loading heavy vLLM dependencies.

validate_models_early() {
  # Find Python - prefer venv if available
  local python_cmd="python3"
  if [ -f "${ROOT_DIR}/.venv/bin/python" ]; then
    python_cmd="${ROOT_DIR}/.venv/bin/python"
  fi

  # Run lightweight validation via Python module
  # Environment variables are read directly by the Python script
  if ! PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
       DEPLOY_MODE="${DEPLOY_MODE:-both}" \
       CHAT_MODEL="${CHAT_MODEL:-}" \
       TOOL_MODEL="${TOOL_MODEL:-}" \
       QUANTIZATION="${QUANTIZATION:-}" \
       CHAT_QUANTIZATION="${CHAT_QUANTIZATION:-}" \
       INFERENCE_ENGINE="${INFERENCE_ENGINE:-${ENGINE_TYPE:-trt}}" \
       "${python_cmd}" -m src.scripts.model_validate; then
    log_err "[validate] ✗ Model validation failed - check model names and allowlists"
    return 1
  fi
  return 0
}
