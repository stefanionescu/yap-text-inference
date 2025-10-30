#!/usr/bin/env bash

# FlashInfer installation helper

install_flashinfer_if_applicable() {
  if [ "$(uname -s)" != "Linux" ]; then
    log_warn "Non-Linux platform detected; skipping FlashInfer GPU wheel install."
    return 0
  fi

  local skip=${SKIP_FLASHINFER:-0}
  if [ "${skip}" = "1" ]; then
    log_info "Skipping FlashInfer install due to configuration"
    return 0
  fi

  local CUDA_NVVER
  CUDA_NVVER=$("${ROOT_DIR}/.venv/bin/python" - <<'PY' || true
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
  TORCH_MAJMIN=$("${ROOT_DIR}/.venv/bin/python" - <<'PY' || true
import sys
try:
    import torch
    ver = torch.__version__.split('+', 1)[0]
    parts = ver.split('.')
    print(f"{parts[0]}.{parts[1]}")  # e.g., 2.7.1 -> 2.7
except Exception:
    sys.exit(1)
PY
  )

  if [ -n "${CUDA_NVVER:-}" ] && [ -n "${TORCH_MAJMIN:-}" ]; then
    local FI_IDX_PRIMARY="https://flashinfer.ai/whl/cu${CUDA_NVVER}/torch${TORCH_MAJMIN}"
    local FI_PKG="flashinfer-python${FLASHINFER_VERSION_SPEC:->=0.2.3,<0.3.2}"
    log_info "Installing ${FI_PKG} (extra-index: ${FI_IDX_PRIMARY})"
    if ! "${ROOT_DIR}/.venv/bin/pip" install --prefer-binary --extra-index-url "${FI_IDX_PRIMARY}" "${FI_PKG}"; then
      log_warn "FlashInfer install failed even with extra index; falling back to PyPI only"
      if ! "${ROOT_DIR}/.venv/bin/pip" install --prefer-binary "${FI_PKG}"; then
        log_warn "FlashInfer NOT installed. Will fall back to XFORMERS at runtime."
      fi
    fi
    log_info "FlashInfer wheel source: ${FI_IDX_PRIMARY} (CUDA=${CUDA_NVVER} Torch=${TORCH_MAJMIN})"
  else
    log_warn "Torch/CUDA not detected; skipping FlashInfer install (will fall back to XFORMERS)."
  fi
}


