#!/usr/bin/env bash

# Shared FlashInfer presence check helper
# Usage: flashinfer_present_py "/path/to/python"

flashinfer_present_py() {
  local py_exe="${1:-}"
  
  # Auto-detect Python if not provided
  if [ -z "${py_exe}" ]; then
    if [ -f "/opt/venv/bin/python" ]; then
      py_exe="/opt/venv/bin/python"
    elif [ -f "${ROOT_DIR:-.}/.venv/bin/python" ]; then
      py_exe="${ROOT_DIR:-.}/.venv/bin/python"
    else
      py_exe="python3"
    fi
  fi

  if [ ! -x "${py_exe}" ] && ! command -v "${py_exe}" >/dev/null 2>&1; then
    return 1
  fi

  if "${py_exe}" - <<'PY' >/dev/null 2>&1
try:
    import flashinfer  # noqa: F401
except Exception:
    raise SystemExit(1)
PY
  then
    return 0
  fi

  return 1
}

