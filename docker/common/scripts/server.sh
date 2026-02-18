#!/usr/bin/env bash
# Shared server launch helpers for Docker runtime scripts.
#
# Provides one canonical uvicorn resolution path and startup sequence used by
# vLLM, TRT, and tool-only images.

resolve_uvicorn_cmd() {
  local root_dir="${1:-/app}"

  if command -v uvicorn >/dev/null 2>&1; then
    UVICORN_CMD=(uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
    return 0
  fi

  if command -v python >/dev/null 2>&1 &&
    PYTHONPATH="${root_dir}${PYTHONPATH:+:${PYTHONPATH}}" python -m src.scripts.validation.package uvicorn >/dev/null 2>&1; then
    UVICORN_CMD=(python -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
    return 0
  fi

  if command -v python3 >/dev/null 2>&1 &&
    PYTHONPATH="${root_dir}${PYTHONPATH:+:${PYTHONPATH}}" python3 -m src.scripts.validation.package uvicorn >/dev/null 2>&1; then
    UVICORN_CMD=(python3 -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
    return 0
  fi

  return 1
}

start_server_with_warmup() {
  local log_prefix="$1"
  local warmup_script="$2"
  local root_dir="${3:-/app}"

  if ! resolve_uvicorn_cmd "${root_dir}"; then
    log_err "[${log_prefix}] ✗ uvicorn not found in container. Ensure dependencies are installed."
    return 127
  fi

  log_info "[${log_prefix}] Starting server..."
  "${UVICORN_CMD[@]}" &
  SERVER_PID=$!

  "${warmup_script}" &

  wait "${SERVER_PID}"
}
