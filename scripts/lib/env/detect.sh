#!/usr/bin/env bash
# =============================================================================
# Environment Detection Helpers
# =============================================================================
# Sources common detection modules and provides HAS_FLASHINFER detection.

_DETECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common modules
source "${_DETECT_DIR}/flashinfer.sh"
source "${_DETECT_DIR}/../common/gpu_detect.sh"
source "${_DETECT_DIR}/../deps/venv.sh"

# Detect FlashInfer availability and set HAS_FLASHINFER
detect_flashinfer() {
  local has=0
  local py_exe
  py_exe="$(get_venv_python)"

  if flashinfer_present_py "${py_exe}"; then
    has=1
  fi
  export HAS_FLASHINFER=${has}
}
