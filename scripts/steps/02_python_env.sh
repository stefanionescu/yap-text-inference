#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${SCRIPT_DIR}/../lib/common/log.sh"

# =============================================================================
# PYTHON VERSION REQUIREMENTS
# =============================================================================
# TensorRT-LLM 1.2.0rc5 requires Python 3.10 specifically.
# Python 3.11 does NOT work reliably (see ADVANCED.md).
# vLLM works with Python 3.10-3.12.

TRT_REQUIRED_PYTHON_VERSION="3.10"

# Install Python 3.10 via deadsnakes PPA (Ubuntu/Debian only)
# This is required for TensorRT-LLM engine
install_python310_deadsnakes() {
  log_info "[python] Installing Python ${TRT_REQUIRED_PYTHON_VERSION} via deadsnakes PPA..."
  
  if ! command -v apt-get >/dev/null 2>&1; then
    log_err "[python] apt-get not available. Python ${TRT_REQUIRED_PYTHON_VERSION} installation requires Ubuntu/Debian."
    log_err "[python] Please install Python ${TRT_REQUIRED_PYTHON_VERSION} manually."
    return 1
  fi
  
  local run_apt="apt-get"
  if [ "$(id -u)" != "0" ]; then
    run_apt="sudo -n apt-get"
  fi
  
  # Add deadsnakes PPA if not already present
  if ! grep -qr "deadsnakes" /etc/apt/sources.list.d/ 2>/dev/null; then
    log_info "[python] Adding deadsnakes PPA..."
    if [ "$(id -u)" = "0" ]; then
      add-apt-repository -y ppa:deadsnakes/ppa || {
        log_err "[python] Failed to add deadsnakes PPA"
        return 1
      }
    else
      sudo -n add-apt-repository -y ppa:deadsnakes/ppa || {
        log_err "[python] Failed to add deadsnakes PPA (may need sudo)"
        return 1
      }
    fi
  fi
  
  # Update and install Python 3.10
  ${run_apt} update -y || {
    log_warn "[python] apt-get update failed, continuing anyway"
  }
  
  DEBIAN_FRONTEND=noninteractive ${run_apt} install -y --no-install-recommends \
    python3.10 python3.10-venv python3.10-dev || {
    log_err "[python] Failed to install Python ${TRT_REQUIRED_PYTHON_VERSION}"
    return 1
  }
  
  log_info "[python] ✓ Python ${TRT_REQUIRED_PYTHON_VERSION} installed successfully"
  return 0
}

# Ensure correct Python version is available for the selected engine
ensure_python_for_engine() {
  local engine="${INFERENCE_ENGINE:-vllm}"
  
  if [ "${engine}" = "trt" ] || [ "${engine}" = "TRT" ]; then
    # TRT requires Python 3.10 specifically
    if command -v "python${TRT_REQUIRED_PYTHON_VERSION}" >/dev/null 2>&1; then
      local py_version
      py_version=$("python${TRT_REQUIRED_PYTHON_VERSION}" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
      if [ "${py_version}" = "${TRT_REQUIRED_PYTHON_VERSION}" ]; then
        log_info "[python] Python ${TRT_REQUIRED_PYTHON_VERSION} available for TRT engine"
        "python${TRT_REQUIRED_PYTHON_VERSION}" --version
        return 0
      fi
    fi
    
    # Python 3.10 not available - try to install it
    log_warn "[python] Python ${TRT_REQUIRED_PYTHON_VERSION} not found. TRT-LLM requires Python ${TRT_REQUIRED_PYTHON_VERSION}."
    log_info "[python] Attempting to install Python ${TRT_REQUIRED_PYTHON_VERSION}..."
    
    if install_python310_deadsnakes; then
      "python${TRT_REQUIRED_PYTHON_VERSION}" --version
      return 0
    else
      log_err "[python] Cannot proceed without Python ${TRT_REQUIRED_PYTHON_VERSION}"
      log_err "[python] TensorRT-LLM 1.2.0rc5 does NOT work with Python 3.11 or 3.12"
      log_err "[python] Please install Python ${TRT_REQUIRED_PYTHON_VERSION} manually:"
      log_err "[python]   Ubuntu/Debian: apt install python3.10 python3.10-venv python3.10-dev"
      log_err "[python]   Or use the Docker image which has Python ${TRT_REQUIRED_PYTHON_VERSION} pre-installed"
      return 1
    fi
  else
    # vLLM: use whatever python3 is available
    log_info "[venv] Ensuring Python and pip are available"
    python3 --version || python --version || true
    python3 -m pip --version || python -m pip --version || true
  fi
  
  return 0
}

# Main: ensure correct Python for engine
ensure_python_for_engine || exit 1


