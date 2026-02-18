#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Early Model Validation
# =============================================================================
# Validates models against allowlists before deployment starts.
# Calls Python to check models without loading heavy vLLM dependencies.

_MODEL_VALIDATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../../config/values/core.sh
source "${_MODEL_VALIDATE_DIR}/../../../config/values/core.sh"
# shellcheck source=../../../config/patterns.sh
source "${_MODEL_VALIDATE_DIR}/../../../config/patterns.sh"

validate_models_early() {
  # Find Python - prefer venv if available
  local python_cmd="python3"
  local deploy_mode="${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}"
  local validate_engine="${INFERENCE_ENGINE:-}"
  if [ -f "${ROOT_DIR}/.venv/bin/python" ]; then
    python_cmd="${ROOT_DIR}/.venv/bin/python"
  fi
  if [ "${deploy_mode}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    validate_engine=""
  fi

  # Run lightweight validation via Python module
  # Environment variables are read directly by the Python script
  if ! PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
    DEPLOY_MODE="${deploy_mode}" \
    CHAT_MODEL="${CHAT_MODEL:-}" \
    TOOL_MODEL="${TOOL_MODEL:-}" \
    CHAT_QUANTIZATION="${CHAT_QUANTIZATION:-}" \
    INFERENCE_ENGINE="${validate_engine}" \
    "${python_cmd}" -m src.scripts.validate; then
    log_err "[validate] ✗ Model validation failed - check model names and allowlists"
    return 1
  fi
  return 0
}
