#!/usr/bin/env bash

# Shared FlashInfer presence check helper
# Usage: flashinfer_present_py "/path/to/python"

flashinfer_present_py() {
  local py_exe="${1:-${ROOT_DIR:-.}/.venv/bin/python}"

  if [ ! -x "${py_exe}" ]; then
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

