#!/usr/bin/env bash
# Model validation for Docker builds (vLLM).
#
# Uses the shared Python validator as the single source of truth.

validate_models_for_deploy() {
  local deploy_mode="$1"
  local chat_model="$2"
  local tool_model="$3"

  local validate_script="${SCRIPT_DIR}/../../../common/download/validate.py"
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[validate] python3 is required for strict model validation" >&2
    return 1
  fi
  if [ ! -f "${validate_script}" ]; then
    echo "[validate] shared validator not found: ${validate_script}" >&2
    return 1
  fi

  DEPLOY_MODE="${deploy_mode}" \
    CHAT_MODEL="${chat_model}" \
    TOOL_MODEL="${tool_model}" \
    ENGINE="vllm" \
    ROOT_DIR="${ROOT_DIR:-}" \
    python3 "${validate_script}"
}
