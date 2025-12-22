#!/usr/bin/env bash

# Virtual environment helpers

# =============================================================================
# PYTHON VERSION REQUIREMENTS
# =============================================================================
# TensorRT-LLM 1.2.0rc5 requires Python 3.10 specifically.
# Python 3.11 does NOT work reliably (see ADVANCED.md).
# vLLM works with Python 3.10-3.12.

TRT_REQUIRED_PYTHON_VERSION="3.10"

# =============================================================================
# VENV PATH HELPERS
# =============================================================================
# Centralized functions to get venv paths - use these instead of hardcoding

# Get the venv directory path
# Usage: get_venv_dir
# Returns: Path to .venv directory (e.g., /path/to/project/.venv)
get_venv_dir() {
  echo "${ROOT_DIR}/.venv"
}

# Get the venv Python executable path
# Usage: get_venv_python
# Returns: Path to venv python binary
get_venv_python() {
  echo "${ROOT_DIR}/.venv/bin/python"
}

# Get the venv pip executable path
# Usage: get_venv_pip
# Returns: Path to venv pip binary
get_venv_pip() {
  echo "${ROOT_DIR}/.venv/bin/pip"
}

# =============================================================================
# PYTHON BINARY SELECTION
# =============================================================================

# Determine the correct Python binary based on engine type
# Usage: get_python_binary_for_engine
# Returns: Python binary name (e.g., python3.10, python3)
get_python_binary_for_engine() {
  local engine="${INFERENCE_ENGINE:-vllm}"
  
  if [ "${engine}" = "trt" ] || [ "${engine}" = "TRT" ]; then
    # TRT requires Python 3.10 specifically
    if command -v "python${TRT_REQUIRED_PYTHON_VERSION}" >/dev/null 2>&1; then
      echo "python${TRT_REQUIRED_PYTHON_VERSION}"
    elif command -v python3.10 >/dev/null 2>&1; then
      echo "python3.10"
    else
      log_err "[venv] Python ${TRT_REQUIRED_PYTHON_VERSION} required for TRT-LLM but not found"
      log_err "[venv] Install it first: bash scripts/steps/02_python_env.sh"
      return 1
    fi
  else
    # vLLM: use system python3
    if command -v python3 >/dev/null 2>&1; then
      echo "python3"
    elif command -v python >/dev/null 2>&1; then
      echo "python"
    else
      log_err "[venv] No Python interpreter found"
      return 1
    fi
  fi
}

# Validate that the venv Python version matches engine requirements
# Usage: validate_venv_python_version <venv_path>
# Returns: 0 if valid, 1 if version mismatch
validate_venv_python_version() {
  local venv_path="$1"
  local venv_python="${venv_path}/bin/python"
  local engine="${INFERENCE_ENGINE:-vllm}"
  
  if [ ! -x "${venv_python}" ]; then
    return 1
  fi
  
  local current_version
  current_version=$("${venv_python}" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null)
  
  if [ "${engine}" = "trt" ] || [ "${engine}" = "TRT" ]; then
    if [ "${current_version}" != "${TRT_REQUIRED_PYTHON_VERSION}" ]; then
      log_warn "[venv] TRT requires Python ${TRT_REQUIRED_PYTHON_VERSION} but venv has ${current_version}"
      return 1
    fi
  fi
  
  return 0
}

ensure_virtualenv() {
  local venv_path="${ROOT_DIR}/.venv"
  local venv_python="${venv_path}/bin/python"
  local engine="${INFERENCE_ENGINE:-vllm}"

  # Check if existing venv has wrong Python version for engine
  if [ -d "${venv_path}" ]; then
    if ! validate_venv_python_version "${venv_path}"; then
      log_warn "[venv] Existing venv has wrong Python version for ${engine} engine; recreating"
      rm -rf "${venv_path}"
    elif [ ! -x "${venv_python}" ]; then
      log_warn "[venv] Existing virtualenv missing python binary; recreating ${venv_path}"
      rm -rf "${venv_path}"
    fi
  fi

  if [ ! -d "${venv_path}" ]; then
    # Get the correct Python binary for this engine
    local PY_BIN
    PY_BIN=$(get_python_binary_for_engine) || return 1
    
    log_info "[venv] Creating virtual environment at ${venv_path} with ${PY_BIN}"

    if ! ${PY_BIN} -m venv "${venv_path}" >/dev/null 2>&1; then
      log_warn "[venv] python venv failed (ensurepip missing?). Trying virtualenv."
      if ! ${PY_BIN} -m pip --version >/dev/null 2>&1; then
        log_warn "[venv] pip is not available; attempting to bootstrap pip."
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
        log_warn "[venv] Failed to upgrade pip; continuing."
      fi
      if ! ${PY_BIN} -m pip install virtualenv >/dev/null 2>&1; then
        log_warn "[venv] virtualenv install failed via pip. Attempting OS package for venv."
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
        log_info "[venv] Creating venv with virtualenv"
        if ${PY_BIN} -m virtualenv --version >/dev/null 2>&1; then
          ${PY_BIN} -m virtualenv "${venv_path}"
        else
          virtualenv -p "${PY_BIN}" "${venv_path}"
        fi
      else
        log_err "[venv] Failed to create a virtual environment. Install python3-venv or virtualenv and retry."
        return 1
      fi
    fi
  fi
}

ensure_pip_in_venv() {
  local venv_python="${ROOT_DIR}/.venv/bin/python"

  if [ ! -x "${venv_python}" ]; then
    log_err "[venv] Virtual environment missing python binary; run ensure_virtualenv first."
    return 1
  fi

  if ! "${venv_python}" -m pip --version >/dev/null 2>&1; then
    log_warn "[venv] pip missing in virtual environment; bootstrapping pip."
    if ! "${venv_python}" -m ensurepip --upgrade >/dev/null 2>&1; then
      TMP_PIP="${ROOT_DIR}/.get-pip.py"
      if command -v curl >/dev/null 2>&1; then
        curl -fsSL -o "${TMP_PIP}" https://bootstrap.pypa.io/get-pip.py || true
      elif command -v wget >/dev/null 2>&1; then
        wget -qO "${TMP_PIP}" https://bootstrap.pypa.io/get-pip.py || true
      fi
      if [ -f "${TMP_PIP}" ]; then
        "${venv_python}" "${TMP_PIP}" || true
        rm -f "${TMP_PIP}" || true
      fi
    fi
  fi

  if "${venv_python}" -m pip --version >/dev/null 2>&1; then
    "${venv_python}" -m pip install --upgrade pip
  else
    log_err "[venv] pip is not available in the virtual environment; please install python3-venv or virtualenv and retry."
    return 1
  fi
}


