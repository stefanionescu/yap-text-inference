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
# PYTHON RUNTIME HELPERS
# =============================================================================

_venv_install_python310_deadsnakes() {
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

  if ! grep -qr "deadsnakes" /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null; then
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

  ${run_apt} update -y || log_warn "[python] apt-get update failed, continuing anyway"

  DEBIAN_FRONTEND=noninteractive ${run_apt} install -y --no-install-recommends \
    python3.10 python3.10-venv python3.10-dev || {
    log_err "[python] Failed to install Python ${TRT_REQUIRED_PYTHON_VERSION}"
    return 1
  }

  log_info "[python] ✓ Python ${TRT_REQUIRED_PYTHON_VERSION} installed successfully"
}

_venv_python_reports_version() {
  local py_bin="$1"
  local expected_minor="${2:-${TRT_REQUIRED_PYTHON_VERSION}}"

  if ! command -v "${py_bin}" >/dev/null 2>&1; then
    return 1
  fi

  local detected_version
  detected_version=$("${py_bin}" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
  if [ "${detected_version}" = "${expected_minor}" ]; then
    local full
    full=$("${py_bin}" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>/dev/null || true)
    log_info "[python] Python ${full} available (${py_bin})"
    return 0
  fi
  return 1
}

ensure_python_runtime_for_engine() {
  local engine="${1:-${INFERENCE_ENGINE:-vllm}}"

  if [[ "${engine,,}" = "trt" ]]; then
    if _venv_python_reports_version "python${TRT_REQUIRED_PYTHON_VERSION}"; then
      return 0
    fi

    log_warn "[python] Python ${TRT_REQUIRED_PYTHON_VERSION} not found. TRT-LLM requires Python ${TRT_REQUIRED_PYTHON_VERSION}."
    log_info "[python] Attempting to install Python ${TRT_REQUIRED_PYTHON_VERSION}..."

    if _venv_install_python310_deadsnakes; then
      return 0
    fi

    log_err "[python] Cannot proceed without Python ${TRT_REQUIRED_PYTHON_VERSION}"
    log_err "[python] TensorRT-LLM 1.2.0rc5 does NOT work with Python 3.11 or 3.12"
    log_err "[python] Please install Python ${TRT_REQUIRED_PYTHON_VERSION} manually:"
    log_err "[python]   Ubuntu/Debian: apt install python3.10 python3.10-venv python3.10-dev"
    log_err "[python]   Or use the Docker image which has Python ${TRT_REQUIRED_PYTHON_VERSION} pre-installed"
    return 1
  fi

  log_info "[python] Ensuring python3 + pip available for vLLM path"
  python3 --version || python --version || true
  python3 -m pip --version || python -m pip --version || true
  return 0
}

# =============================================================================
# VENV PATH HELPERS
# =============================================================================
# Centralized functions to get venv paths - use these instead of hardcoding

# Resolve the venv directory with the following precedence:
# 1) VENV_DIR env var (explicit override)
# 2) Prebaked /opt/venv if it exists (TRT base image comes with this)
# 3) Repo-local .venv
resolve_venv_dir() {
  if [ -n "${VENV_DIR:-}" ]; then
    echo "${VENV_DIR}"
    return
  fi
  if [ -d "/opt/venv" ]; then
    echo "/opt/venv"
    return
  fi
  echo "${ROOT_DIR}/.venv"
}

# Get the venv directory path (export-friendly)
get_venv_dir() {
  resolve_venv_dir
}

# Get the venv Python executable path
# Usage: get_venv_python
# Returns: Path to venv python binary
get_venv_python() {
  printf '%s/bin/python\n' "$(get_venv_dir)"
}

# Get the venv pip executable path
# Usage: get_venv_pip
# Returns: Path to venv pip binary
get_venv_pip() {
  printf '%s/bin/pip\n' "$(get_venv_dir)"
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
  local venv_path
  venv_path="$(resolve_venv_dir)"
  export VENV_DIR="${venv_path}"
  local venv_python="${venv_path}/bin/python"
  local engine="${INFERENCE_ENGINE:-vllm}"

  # Check if existing venv has wrong Python version for engine
  if [ -d "${venv_path}" ]; then
    if ! validate_venv_python_version "${venv_path}"; then
      if [ "${venv_path}" = "/opt/venv" ]; then
        log_err "[venv] /opt/venv exists but has incompatible Python for ${engine}; refusing to delete baked venv"
        return 1
      fi
      log_warn "[venv] Existing venv has wrong Python version for ${engine} engine; recreating"
      rm -rf "${venv_path}"
    elif [ ! -x "${venv_python}" ]; then
      if [ "${venv_path}" = "/opt/venv" ]; then
        log_err "[venv] /opt/venv missing python binary; refusing to delete baked venv"
        return 1
      fi
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
  local venv_path
  venv_path="$(resolve_venv_dir)"
  export VENV_DIR="${venv_path}"
  local venv_python="${venv_path}/bin/python"

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

# Activate virtual environment
# Usage: activate_venv [venv_dir] [fail_on_error]
#   venv_dir: Path to venv directory (defaults to ${ROOT_DIR}/.venv)
#   fail_on_error: If 1, exit on error; if 0, return error code (default: 1)
# Returns: 0 on success, 1 on failure
activate_venv() {
  local venv_dir="${1:-$(resolve_venv_dir)}"
  local fail_on_error="${2:-1}"
  
  if [ ! -d "${venv_dir}" ]; then
    log_err "[venv] Virtual environment not found at ${venv_dir}"
    if [ "${fail_on_error}" = "1" ]; then
      exit 1
    fi
    return 1
  fi
  
  if [ ! -f "${venv_dir}/bin/activate" ]; then
    log_err "[venv] Virtual environment corrupted (no activate script) at ${venv_dir}"
    if [ "${fail_on_error}" = "1" ]; then
      exit 1
    fi
    return 1
  fi
  
  # shellcheck disable=SC1091
  source "${venv_dir}/bin/activate" || {
    log_err "[venv] Failed to activate virtual environment at ${venv_dir}"
    if [ "${fail_on_error}" = "1" ]; then
      exit 1
    fi
    return 1
  }
  
  return 0
}


