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
  
  # Validate Python binary exists - check multiple locations
  if [ ! -x "${venv_python}" ]; then
    if [ -x "/opt/venv/bin/python" ]; then
      venv_python="/opt/venv/bin/python"
      venv_pip="/opt/venv/bin/pip"
    elif command -v python3 >/dev/null 2>&1; then
      venv_python="python3"
      venv_pip="python3 -m pip"
    else
      log_warn "[deps] ⚠ No Python found; skipping FlashInfer install"
      return 0
    fi
  fi

  # Detect CUDA and Torch versions
  local torch_info CUDA_NVVER TORCH_MAJMIN
  torch_info=$("${venv_python}" -c "
import sys
try:
    import torch
    cu = (torch.version.cuda or '').strip()
    ver = torch.__version__.split('+', 1)[0]
    parts = ver.split('.')
    torch_majmin = f'{parts[0]}.{parts[1]}'
    cuda_ver = cu.replace('.', '') if cu else ''
    print(f'{cuda_ver} {torch_majmin}')
except Exception:
    sys.exit(1)
" 2>/dev/null) || torch_info=""

  if [ -n "${torch_info}" ]; then
    CUDA_NVVER="${torch_info%% *}"
    TORCH_MAJMIN="${torch_info##* }"
  fi

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


