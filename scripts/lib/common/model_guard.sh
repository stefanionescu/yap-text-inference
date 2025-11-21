#!/usr/bin/env bash

# Helper functions to ensure chat/tool models are part of the approved allowlist
# before kicking off long-running deployment scripts.

_model_guard_is_local_path() {
  local path="$1"
  if [ -z "${path}" ]; then
    return 1
  fi
  if [[ "${path}" == /* ]] || [[ "${path}" == .* ]]; then
    if [ -e "${path}" ]; then
      return 0
    fi
  fi
  if [ -e "${ROOT_DIR}/${path}" ]; then
    return 0
  fi
  return 1
}

_model_guard_python_check() {
  local kind="$1"
  local name="$2"
  PYTHONPATH="${ROOT_DIR}" python3 - "$kind" "$name" <<'PY'
import sys
from src.config.models import ALLOWED_CHAT_MODELS, ALLOWED_TOOL_MODELS

kind = sys.argv[1]
model = sys.argv[2].strip()
if not model:
    raise SystemExit(0)

allowed = ALLOWED_CHAT_MODELS if kind == "chat" else ALLOWED_TOOL_MODELS
if model in allowed:
    raise SystemExit(0)

pretty = ", ".join(allowed)
sys.stderr.write(
    f"{kind.capitalize()} model '{model}' is not in the allowlist. "
    f"Choose one of: {pretty}\n"
)
raise SystemExit(1)
PY
}

ensure_model_allowed() {
  local kind="$1"
  local name="$2"

  if [ -z "${name:-}" ]; then
    return 0
  fi

  if _model_guard_is_local_path "${name}"; then
    return 0
  fi

  if _model_guard_python_check "${kind}" "${name}"; then
    return 0
  fi

  log_error "Invalid ${kind} model '${name}'. See message above for allowed options."
  exit 1
}


