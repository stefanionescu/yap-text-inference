#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

_push_log() {
  local ctx="${1:-push}"
  shift
  echo "[push:${ctx}] $*"
}

_push_require_env() {
  local ctx="$1"

  if [[ "${ORPHEUS_PRECISION_MODE:-quantized}" != "quantized" ]]; then
    _push_log "$ctx" "ERROR: Hugging Face pushes only supported for ORPHEUS_PRECISION_MODE=quantized"
    return 1
  fi
  if [[ -z "${GPU_SM_ARCH:-}" ]]; then
    _push_log "$ctx" "ERROR: GPU_SM_ARCH must be set (e.g., sm80 | sm89 | sm90)"
    return 1
  fi
  if [[ -z "${HF_PUSH_REPO_ID:-}" ]]; then
    _push_log "$ctx" "ERROR: HF_PUSH_REPO_ID is required"
    return 1
  fi
  return 0
}

_push_python_exec() {
  local candidate="${PYTHON_EXEC:-}"
  if [[ -n "$candidate" ]]; then
    echo "$candidate"
    return 0
  fi
  if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
    echo "${ROOT_DIR}/.venv/bin/python"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi
  return 1
}

cmd_validate() {
  local ctx="${1:-push}"
  if _push_require_env "$ctx"; then
    _push_log "$ctx" "HF push validation passed:"
    _push_log "$ctx" "  GPU_SM_ARCH: ${GPU_SM_ARCH}"
    _push_log "$ctx" "  HF_PUSH_REPO_ID: ${HF_PUSH_REPO_ID}"
    _push_log "$ctx" "  HF_PUSH_PRIVATE: ${HF_PUSH_PRIVATE:-1}"
    return 0
  fi
  return 1
}

cmd_run() {
  local ctx="${1:-push}"
  _push_require_env "$ctx"
  local py
  if ! py=$(_push_python_exec); then
    _push_log "$ctx" "ERROR: Unable to locate python interpreter for Hugging Face push"
    return 1
  fi
  local cmd=(
    "$py" "${ROOT_DIR}/server/hf/push_to_hf.py"
    --repo-id "${HF_PUSH_REPO_ID}"
    --what "${HF_PUSH_WHAT:-both}"
  )
  if [[ "${HF_PUSH_PRIVATE:-1}" = "1" ]]; then
    cmd+=(--private)
  fi
  if [[ -n "${HF_PUSH_ENGINE_LABEL:-}" ]]; then
    cmd+=(--engine-label "${HF_PUSH_ENGINE_LABEL}")
  fi
  if [[ "${HF_PUSH_PRUNE:-0}" = "1" ]]; then
    cmd+=(--prune)
  fi
  if [[ "${HF_PUSH_NO_README:-0}" = "1" ]]; then
    cmd+=(--no-readme)
  fi
  _push_log "$ctx" "Pushing artifacts to Hugging Face..."
  "${cmd[@]}"
  _push_log "$ctx" "HF push completed successfully"
}

case "${1:-}" in
  validate)
    shift
    cmd_validate "${1:-push}"
    ;;
  run)
    shift
    cmd_run "${1:-push}"
    ;;
  *)
    echo "Usage: $0 {validate|run} [context]" >&2
    exit 1
    ;;
esac

