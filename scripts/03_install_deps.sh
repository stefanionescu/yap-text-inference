#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Installing Python dependencies"

export PIP_ROOT_USER_ACTION=${PIP_ROOT_USER_ACTION:-ignore}
export PIP_DISABLE_PIP_VERSION_CHECK=${PIP_DISABLE_PIP_VERSION_CHECK:-1}
export PIP_NO_INPUT=${PIP_NO_INPUT:-1}
export PIP_PREFER_BINARY=${PIP_PREFER_BINARY:-1}
# Prefer AOT kernels for FlashInfer to avoid long first-run JIT compiles
export FLASHINFER_ENABLE_AOT=${FLASHINFER_ENABLE_AOT:-1}

# Ensure correct CUDA arch is visible during build steps (FlashInfer, etc.)
if [ -z "${TORCH_CUDA_ARCH_LIST:-}" ]; then
  if command -v nvidia-smi >/dev/null 2>&1; then
    CAP=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -n 1 2>/dev/null || true)
    if [ -n "${CAP}" ]; then
      export TORCH_CUDA_ARCH_LIST="${CAP}"
      log_info "Detected compute capability: ${TORCH_CUDA_ARCH_LIST}"
    else
      export TORCH_CUDA_ARCH_LIST=8.0
      log_warn "Could not detect compute capability; defaulting TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}"
    fi
  else
    export TORCH_CUDA_ARCH_LIST=8.0
    log_warn "nvidia-smi not found; defaulting TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}"
  fi
fi

if [ ! -d "${ROOT_DIR}/.venv" ]; then
  log_info "Creating virtual environment at ${ROOT_DIR}/.venv"
  python -m venv "${ROOT_DIR}/.venv"
fi

"${ROOT_DIR}/.venv/bin/python" -m pip install --upgrade pip

# Skip reinstall if requirements.txt didn't change since last successful install (unless FORCE_REINSTALL=1)
REQ_FILE="${ROOT_DIR}/requirements.txt"
STAMP_FILE="${ROOT_DIR}/.venv/.req_hash"
SKIP_REQ_INSTALL=0
if [ "${FORCE_REINSTALL:-0}" != "1" ] && [ -f "${STAMP_FILE}" ] && [ -f "${REQ_FILE}" ]; then
  CUR_HASH=$(sha256sum "${REQ_FILE}" | awk '{print $1}')
  OLD_HASH=$(cat "${STAMP_FILE}" 2>/dev/null || true)
  if [ "${CUR_HASH}" = "${OLD_HASH}" ]; then
    log_info "Dependencies unchanged; skipping main pip install"
    SKIP_REQ_INSTALL=1
  fi
fi

# Install all requirements EXCEPT FlashInfer first, so we can pick the correct FlashInfer wheel afterward.
TMP_REQ_FILE="${ROOT_DIR}/.venv/.requirements.no_flashinfer.txt"
if [ -f "${REQ_FILE}" ]; then
  # Filter out any line that starts with flashinfer-python (allow trailing constraints or comments)
  grep -v -E '^\s*flashinfer-python(\s|$|==|>=|<=|~=|!=)' "${REQ_FILE}" > "${TMP_REQ_FILE}" || cp "${REQ_FILE}" "${TMP_REQ_FILE}" || true
fi

if [ "${SKIP_REQ_INSTALL}" -ne 1 ]; then
  "${ROOT_DIR}/.venv/bin/pip" install --upgrade-strategy only-if-needed -r "${TMP_REQ_FILE}"
fi

# Attempt GPU-aware FlashInfer install if we're on Linux with CUDA/Torch available.
# This prefers official FlashInfer wheel indices by CUDA/Torch version, and falls back gracefully.
if [ "$(uname -s)" = "Linux" ]; then
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
    FI_IDX_PRIMARY="https://flashinfer.ai/whl/cu${CUDA_NVVER}/torch${TORCH_MAJMIN}"
    log_info "Installing flashinfer-python (extra-index: ${FI_IDX_PRIMARY})"
    if ! "${ROOT_DIR}/.venv/bin/pip" install --prefer-binary --extra-index-url "${FI_IDX_PRIMARY}" flashinfer-python; then
      log_warn "FlashInfer install failed even with extra index; falling back to PyPI only"
      if ! "${ROOT_DIR}/.venv/bin/pip" install --prefer-binary flashinfer-python; then
        log_warn "FlashInfer NOT installed. Will fall back to XFORMERS at runtime."
      fi
    fi
    log_info "FlashInfer wheel source: ${FI_IDX_PRIMARY} (CUDA=${CUDA_NVVER} Torch=${TORCH_MAJMIN})"
  else
    log_warn "Torch/CUDA not detected; skipping FlashInfer install (will fall back to XFORMERS)."
  fi
else
  log_warn "Non-Linux platform detected; skipping FlashInfer GPU wheel install."
fi

# Record the hash after a successful install
if [ -f "${REQ_FILE}" ]; then
  sha256sum "${REQ_FILE}" | awk '{print $1}' > "${STAMP_FILE}" || true
fi


