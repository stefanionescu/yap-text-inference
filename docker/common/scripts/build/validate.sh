#!/usr/bin/env bash
# Shared model validation for Docker builds.
#
# Uses docker/common/download/validate.py as the single source of truth.

validate_models_for_deploy_common() {
  local engine="$1"
  local deploy_mode="$2"
  local chat_model="$3"
  local tool_model="$4"
  local trt_engine_repo="${5:-}"
  local trt_engine_label="${6:-}"

  local validate_script="${ROOT_DIR}/docker/common/download/validate.py"
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
    TRT_ENGINE_REPO="${trt_engine_repo}" \
    TRT_ENGINE_LABEL="${trt_engine_label}" \
    ENGINE="${engine}" \
    ROOT_DIR="${ROOT_DIR:-}" \
    python3 "${validate_script}"
}
