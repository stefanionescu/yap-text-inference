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

# Ensure CA certificates are present for HTTPS (HF downloads)
if [ "$(uname -s)" = "Linux" ] && [ ! -f "/etc/ssl/certs/ca-certificates.crt" ]; then
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -y >/dev/null 2>&1 || true
    apt-get install -y ca-certificates >/dev/null 2>&1 || true
    update-ca-certificates >/dev/null 2>&1 || true
  elif command -v apk >/dev/null 2>&1; then
    apk add --no-cache ca-certificates >/dev/null 2>&1 || true
    update-ca-certificates >/dev/null 2>&1 || true
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y ca-certificates >/dev/null 2>&1 || true
    update-ca-trust >/dev/null 2>&1 || true
  elif command -v yum >/dev/null 2>&1; then
    yum install -y ca-certificates >/dev/null 2>&1 || true
    update-ca-trust >/dev/null 2>&1 || true
  fi
fi

if [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
  export REQUESTS_CA_BUNDLE=${REQUESTS_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}
  export CURL_CA_BUNDLE=${CURL_CA_BUNDLE:-/etc/ssl/certs/ca-certificates.crt}
  export GIT_SSL_CAINFO=${GIT_SSL_CAINFO:-/etc/ssl/certs/ca-certificates.crt}
fi

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
  # Prefer python3 if available
  PY_BIN="python3"
  if ! command -v ${PY_BIN} >/dev/null 2>&1; then
    PY_BIN="python"
  fi

  if ! ${PY_BIN} -m venv "${ROOT_DIR}/.venv" >/dev/null 2>&1; then
    log_warn "python venv failed (ensurepip missing?). Trying virtualenv."
    # Try to install virtualenv with system pip
    if ! ${PY_BIN} -m pip --version >/dev/null 2>&1; then
      log_warn "pip is not available; attempting to bootstrap pip."
      # Try get-pip.py as a last resort
      TMP_PIP="${ROOT_DIR}/.get-pip.py"
      if command -v curl >/dev/null 2>&1; then
        curl -fsSL -o "${TMP_PIP}" https://bootstrap.pypa.io/get-pip.py || true
      elif command -v wget >/dev/null 2>&1; then
        wget -qO "${TMP_PIP}" https://bootstrap.pypa.io/get-pip.py || true
      fi
      if [ -f "${TMP_PIP}" ]; then
        ${PY_BIN} "${TMP_PIP}" || true
        rm -f "${TMP_PIP}" || true
      fi
    fi

    if ! ${PY_BIN} -m pip install --upgrade pip >/dev/null 2>&1; then
      log_warn "Failed to upgrade pip; continuing."
    fi
    if ! ${PY_BIN} -m pip install virtualenv >/dev/null 2>&1; then
      log_warn "virtualenv install failed via pip. Attempting OS package for venv."
      # Attempt common OS package managers (non-interactive)
      if command -v apt-get >/dev/null 2>&1; then
        sudo -n apt-get update >/dev/null 2>&1 || true
        sudo -n apt-get install -y python3-venv >/dev/null 2>&1 || true
      elif command -v apk >/dev/null 2>&1; then
        sudo -n apk add --no-cache python3 py3-virtualenv >/dev/null 2>&1 || true
      elif command -v dnf >/dev/null 2>&1; then
        sudo -n dnf install -y python3-venv >/dev/null 2>&1 || true
      elif command -v yum >/dev/null 2>&1; then
        sudo -n yum install -y python3-venv >/dev/null 2>&1 || true
      fi
    fi

    if command -v virtualenv >/dev/null 2>&1 || ${PY_BIN} -m virtualenv --version >/dev/null 2>&1; then
      log_info "Creating venv with virtualenv"
      # Prefer module invocation to ensure correct interpreter
      if ${PY_BIN} -m virtualenv --version >/dev/null 2>&1; then
        ${PY_BIN} -m virtualenv "${ROOT_DIR}/.venv"
      else
        virtualenv -p "${PY_BIN}" "${ROOT_DIR}/.venv"
      fi
    else
      log_err "Failed to create a virtual environment. Install python3-venv or virtualenv and retry."
      exit 1
    fi
  fi
fi

# Ensure pip is available inside the virtual environment (handle broken venvs)
if ! "${ROOT_DIR}/.venv/bin/python" -m pip --version >/dev/null 2>&1; then
  log_warn "pip missing in virtual environment; bootstrapping pip."
  if ! "${ROOT_DIR}/.venv/bin/python" -m ensurepip --upgrade >/dev/null 2>&1; then
    TMP_PIP="${ROOT_DIR}/.get-pip.py"
    if command -v curl >/dev/null 2>&1; then
      curl -fsSL -o "${TMP_PIP}" https://bootstrap.pypa.io/get-pip.py || true
    elif command -v wget >/dev/null 2>&1; then
      wget -qO "${TMP_PIP}" https://bootstrap.pypa.io/get-pip.py || true
    fi
    if [ -f "${TMP_PIP}" ]; then
      "${ROOT_DIR}/.venv/bin/python" "${TMP_PIP}" || true
      rm -f "${TMP_PIP}" || true
    fi
  fi
fi

if "${ROOT_DIR}/.venv/bin/python" -m pip --version >/dev/null 2>&1; then
  "${ROOT_DIR}/.venv/bin/python" -m pip install --upgrade pip
else
  log_err "pip is not available in the virtual environment; please install python3-venv or virtualenv and retry."
  exit 1
fi

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
  SKIP_FLASHINFER=${SKIP_FLASHINFER:-0}

  if [ "${SKIP_FLASHINFER}" != "1" ]; then
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
      FI_PKG="flashinfer-python${FLASHINFER_VERSION_SPEC:->=0.2.3,<0.3.2}"
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
  else
    log_info "Skipping FlashInfer install due to configuration"
  fi
else
  log_warn "Non-Linux platform detected; skipping FlashInfer GPU wheel install."
fi

# Record the hash after a successful install
if [ -f "${REQ_FILE}" ]; then
  sha256sum "${REQ_FILE}" | awk '{print $1}' > "${STAMP_FILE}" || true
fi
