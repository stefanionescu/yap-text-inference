#!/usr/bin/env bash

# Environment detection helpers (FlashInfer, GPU name)

source "${BASH_SOURCE[0]%/*}/flashinfer.sh"

detect_flashinfer() {
  local has=0
  if flashinfer_present_py "${ROOT_DIR}/.venv/bin/python"; then
    has=1
  fi
  export HAS_FLASHINFER=${has}
}

detect_gpu_name() {
  local gpu_name=""
  if command -v nvidia-smi >/dev/null 2>&1; then
    gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 || true)
  fi
  export DETECTED_GPU_NAME="${gpu_name}"
}


