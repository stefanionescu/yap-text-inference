#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# FlashInfer Installation
# =============================================================================
# Handles FlashInfer wheel installation with CUDA version detection.
# FlashInfer provides optimized attention kernels for vLLM.

_FI_DEP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${_FI_DEP_DIR}/venv.sh"

install_flashinfer_if_applicable() {
  local scope="${1:-deps}"
  local python_bin="${2:-}"
  local pip_bin="${3:-}"
  local label
  case "${scope}" in
    \[*\]) label="${scope}" ;;
    *) label="[${scope}]" ;;
  esac

  if [ "$(uname -s)" != "Linux" ]; then
    log_warn "${label} ⚠ Non-Linux platform detected; skipping FlashInfer GPU wheel install."
    return 0
  fi

  local skip=${SKIP_FLASHINFER:-0}
  if [ "${skip}" = "1" ]; then
    log_info "${label} Skipping FlashInfer install due to configuration"
    return 0
  fi

  if [ -z "${python_bin}" ]; then
    python_bin="$(get_venv_python 2>/dev/null || true)"
  fi
  if [ -z "${python_bin}" ] || [ ! -x "${python_bin}" ]; then
    if [ -x "/opt/venv/bin/python" ]; then
      python_bin="/opt/venv/bin/python"
    else
      python_bin="$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)"
    fi
  fi
  if [ -z "${python_bin}" ]; then
    log_warn "${label} ⚠ No Python found; skipping FlashInfer install"
    return 0
  fi

  if [ -z "${pip_bin}" ]; then
    pip_bin="$(get_venv_pip 2>/dev/null || true)"
  fi
  if [ -z "${pip_bin}" ] || [ ! -x "${pip_bin}" ]; then
    if [ -x "/opt/venv/bin/pip" ]; then
      pip_bin="/opt/venv/bin/pip"
    elif command -v pip3 >/dev/null 2>&1; then
      pip_bin="$(command -v pip3)"
    elif command -v pip >/dev/null 2>&1; then
      pip_bin="$(command -v pip)"
    else
      pip_bin=""
    fi
  fi
  local -a pip_cmd
  if [ -n "${pip_bin}" ]; then
    pip_cmd=("${pip_bin}")
  else
    pip_cmd=("${python_bin}" "-m" "pip")
  fi

  # Detect CUDA and Torch versions
  local torch_info CUDA_NVVER TORCH_MAJMIN
  torch_info=$("${python_bin}" -c "
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
    log_info "${label} Installing flashinfer-python..."
    if ! pip_quiet_exec "${pip_cmd[@]}" install --prefer-binary --extra-index-url "${FI_IDX_PRIMARY}" "${FI_PKG}"; then
      log_warn "${label} ⚠ FlashInfer install failed with extra index; falling back to PyPI only"
      if ! pip_quiet_exec "${pip_cmd[@]}" install --prefer-binary "${FI_PKG}"; then
        log_warn "${label} ⚠ FlashInfer NOT installed. Will fall back to XFORMERS at runtime."
      fi
    fi
  else
    log_warn "${label} ⚠ Torch/CUDA not detected; skipping FlashInfer install (will fall back to XFORMERS)."
  fi
}
