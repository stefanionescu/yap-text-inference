#!/usr/bin/env bash
# Model validation for Docker builds (vLLM)
#
# Uses Python validation module to ensure consistency with src/config.

# Validate models based on deploy mode using Python config
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
  _validate_models_shell "$@"
}

# Shell fallback validation (for environments without Python)
_validate_models_shell() {
  local deploy_mode="$1"
  local chat_model="$2"
  local tool_model="$3"
  local errors=0

  case "$deploy_mode" in
    chat)
      _validate_chat_model_shell "$chat_model" || ((errors++))
      ;;
    tool)
      _validate_tool_model_shell "$tool_model" || ((errors++))
      ;;
    both)
      _validate_chat_model_shell "$chat_model" || ((errors++))
      _validate_tool_model_shell "$tool_model" || ((errors++))
      ;;
    *)
      echo "[validate] Invalid DEPLOY_MODE: '$deploy_mode'. Must be chat|tool|both" >&2
      ((errors++))
      ;;
  esac

  return $errors
}

# Shell validation for chat model
_validate_chat_model_shell() {
  local model="$1"
  if [[ -z $model ]]; then
    echo "[validate] CHAT_MODEL is required but not set" >&2
    return 1
  fi

  # Check for HF repo format
  if [[ $model != *"/"* ]]; then
    echo "[validate] CHAT_MODEL '$model' is not a valid HuggingFace repo format" >&2
    return 1
  fi

  # Check for pre-quantized markers (synced with AWQ_MODEL_MARKERS)
  local lowered
  lowered=$(echo "$model" | tr '[:upper:]' '[:lower:]')

  local markers=("awq" "gptq" "w4a16" "compressed-tensors" "autoround")
  local found=0
  for marker in "${markers[@]}"; do
    if [[ $lowered == *"$marker"* ]]; then
      found=1
      break
    fi
  done

  if [[ $found -eq 0 ]]; then
    echo "[validate] CHAT_MODEL '$model' is not a pre-quantized model" >&2
    echo "[validate] Chat model name must contain one of: ${markers[*]}" >&2
    return 1
  fi

  echo "[validate] CHAT_MODEL: $model"
  return 0
}

# Shell validation for tool model
_validate_tool_model_shell() {
  local model="$1"
  if [[ -z $model ]]; then
    echo "[validate] TOOL_MODEL is required but not set" >&2
    return 1
  fi

  # Allowed tool models (synced with src/config/models.py:ALLOWED_TOOL_MODELS)
  local allowed_models=(
    "yapwithai/yap-longformer-screenshot-intent"
    "yapwithai/yap-modernbert-screenshot-intent"
  )

  for allowed in "${allowed_models[@]}"; do
    if [[ $model == "$allowed" ]]; then
      echo "[validate] TOOL_MODEL: $model"
      return 0
    fi
  done

  echo "[validate] TOOL_MODEL '$model' is not in the allowed list" >&2
  echo "[validate] See src/config/models.py for allowed tool models" >&2
  return 1
}
