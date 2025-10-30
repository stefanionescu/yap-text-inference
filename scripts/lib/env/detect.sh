#!/usr/bin/env bash

# Environment detection helpers (FlashInfer, GPU name)

detect_flashinfer() {
  local has=0
  if [ -f "${ROOT_DIR}/.venv/bin/python" ]; then
    if "${ROOT_DIR}/.venv/bin/python" - <<'PY' >/dev/null 2>&1
try:
    import flashinfer  # noqa: F401
except Exception:
    raise SystemExit(1)
PY
    then
      has=1
    fi
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


