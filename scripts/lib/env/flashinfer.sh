#!/usr/bin/env bash
# =============================================================================
# FlashInfer Detection
# =============================================================================
# Checks whether FlashInfer is available in the Python environment.
# FlashInfer provides optimized attention kernels for vLLM.

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

  local python_root="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  if PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
     "${py_exe}" -m src.scripts.env_check flashinfer-check >/dev/null 2>&1; then
    return 0
  fi

  return 1
}

