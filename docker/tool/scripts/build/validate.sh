#!/usr/bin/env bash
# Model validation for Docker builds (tool-only)
#
# Simplified: only validates TOOL_MODEL. No chat model or engine validation.

# Validate models based on deploy mode
# Usage: validate_models_for_deploy <deploy_mode> <chat_model> <tool_model>
validate_models_for_deploy() {
  local deploy_mode="$1"
  local chat_model="$2"
  local tool_model="$3"

  # Try Python validation first (uses src/config as source of truth)
  if command -v python3 >/dev/null 2>&1; then
    local validate_script="${SCRIPT_DIR}/../../../common/download/validate.py"
    if [ -f "${validate_script}" ]; then
      DEPLOY_MODE="${deploy_mode}" \
        CHAT_MODEL="${chat_model}" \
        TOOL_MODEL="${tool_model}" \
        ENGINE="vllm" \
        ROOT_DIR="${ROOT_DIR:-}" \
        python3 "${validate_script}"
      return $?
    fi
  fi

  # Fallback to shell validation if Python not available
  _validate_tool_model_shell "${tool_model}"
}

# Shell validation for tool model (format-only; canonical list enforced in src/helpers/models.is_tool_model())
_validate_tool_model_shell() {
  local model="$1"
  if [[ -z $model ]]; then
    echo "[validate] TOOL_MODEL is required but not set" >&2
    return 1
  fi

  if [[ $model != *"/"* ]]; then
    echo "[validate] TOOL_MODEL '$model' is not a valid HuggingFace repo format (owner/repo)" >&2
    return 1
  fi

  echo "[validate] TOOL_MODEL: $model"
  return 0
}
