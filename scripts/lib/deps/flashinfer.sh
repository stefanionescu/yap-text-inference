#!/usr/bin/env bash

# FlashInfer installation helper

_FI_DEP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_FI_DEP_DIR}/venv.sh"

install_flashinfer_if_applicable() {
  if [ "$(uname -s)" != "Linux" ]; then
    log_warn "[deps] ⚠ Non-Linux platform detected; skipping FlashInfer GPU wheel install."
    return 0
  fi

  local skip=${SKIP_FLASHINFER:-0}
  if [ "${skip}" = "1" ]; then
    log_info "[deps] Skipping FlashInfer install due to configuration"
    return 0
  fi

  local venv_python venv_pip
  venv_python="$(get_venv_python)"
  venv_pip="$(get_venv_pip)"

  local CUDA_NVVER
  CUDA_NVVER=$("${venv_python}" - <<'PY' || true
import sys
try:
    import torch
    cu = (torch.version.cuda or '').strip()
    if not cu:
        sys.exit(1)
    print(cu.replace('.', ''))  # e.g., 12.6 -> 126
except Exception:
    sys.exit(1)
PY
  )

  local TORCH_MAJMIN
  TORCH_MAJMIN=$("${venv_python}" - <<'PY' || true
import sys
try:
    import torch
    ver = torch.__version__.split('+', 1)[0]
    parts = ver.split('.')
    print(f"{parts[0]}.{parts[1]}")  # e.g., 2.9.0 -> 2.9
except Exception:
    sys.exit(1)
PY
  )

  if [ -n "${CUDA_NVVER:-}" ] && [ -n "${TORCH_MAJMIN:-}" ]; then
    local FI_IDX_PRIMARY="https://flashinfer.ai/whl/cu${CUDA_NVVER}/torch${TORCH_MAJMIN}"
    local FI_PKG="flashinfer-python${FLASHINFER_VERSION_SPEC:-==0.5.3}"
    log_info "[deps] Installing ${FI_PKG} (extra-index: ${FI_IDX_PRIMARY})"
    if ! "${venv_pip}" install --prefer-binary --extra-index-url "${FI_IDX_PRIMARY}" "${FI_PKG}"; then
      log_warn "[deps] ⚠ FlashInfer install failed even with extra index; falling back to PyPI only"
      if ! "${venv_pip}" install --prefer-binary "${FI_PKG}"; then
        log_warn "[deps] ⚠ FlashInfer NOT installed. Will fall back to XFORMERS at runtime."
      fi
    fi
    log_info "[deps] FlashInfer wheel source: ${FI_IDX_PRIMARY} (CUDA=${CUDA_NVVER} Torch=${TORCH_MAJMIN})"
  else
    log_warn "[deps] ⚠ Torch/CUDA not detected; skipping FlashInfer install (will fall back to XFORMERS)."
  fi
}


