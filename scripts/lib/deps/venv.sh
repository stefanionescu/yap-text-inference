#!/usr/bin/env bash

# Virtual environment helpers.

_VENV_HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./pip.sh
source "${_VENV_HELPERS_DIR}/pip.sh"
# shellcheck source=../common/constants.sh
source "${_VENV_HELPERS_DIR}/../common/constants.sh"

# =============================================================================
# PYTHON RUNTIME HELPERS
# =============================================================================

_venv_install_python310_deadsnakes() {
  log_info "[python] Installing Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION} via deadsnakes PPA..."

  if ! command -v apt-get >/dev/null 2>&1; then
    log_err "[python] ✗ apt-get not available. Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION} installation requires Ubuntu/Debian."
    log_err "[python] ✗ Please install Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION} manually."
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
        log_err "[python] ✗ Failed to add deadsnakes PPA"
        return 1
      }
    else
      sudo -n add-apt-repository -y ppa:deadsnakes/ppa || {
        log_err "[python] ✗ Failed to add deadsnakes PPA (may need sudo)"
        return 1
      }
    fi
  fi

  ${run_apt} update -y || log_warn "[python] ⚠ apt-get update failed, continuing anyway"

  DEBIAN_FRONTEND=noninteractive ${run_apt} install -y --no-install-recommends \
    python3.10 python3.10-venv python3.10-dev || {
    log_err "[python] ✗ Failed to install Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION}"
    return 1
  }

  log_info "[python] ✓ Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION} installed successfully"
}

_venv_python_reports_version() {
  local py_bin="$1"
  local expected_minor="${2:-${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION}}"

  if ! command -v "${py_bin}" >/dev/null 2>&1; then
    return 1
  fi

  local detected_version
  detected_version=$("${py_bin}" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
  if [ "${detected_version}" = "${expected_minor}" ]; then
    return 0
  fi
  return 1
}

ensure_python_runtime_for_engine() {
  local engine="${1:-${INFERENCE_ENGINE:-vllm}}"

  if [[ "${engine,,}" = "trt" ]]; then
    if _venv_python_reports_version "python${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION}"; then
      return 0
    fi

    log_warn "[python] ⚠ Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION} not found. TRT-LLM requires Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION}."
    log_info "[python] Attempting to install Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION}..."

    if _venv_install_python310_deadsnakes; then
      return 0
    fi

    log_err "[python] ✗ Cannot proceed without Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION}"
    log_err "[python]   TensorRT-LLM 1.2.0rc5 does NOT work with Python 3.11 or 3.12"
    log_err "[python]   Please install Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION} manually:"
    log_err "[python]     Ubuntu/Debian: apt install python3.10 python3.10-venv python3.10-dev"
    log_err "[python]     Or use the Docker image which has Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION} pre-installed"
    return 1
  fi

  log_info "[python] Ensuring python3 + pip available for vLLM path..."
  { python3 --version || python --version; } &>/dev/null || true
  { python3 -m pip --version || python -m pip --version; } &>/dev/null || true
  return 0
}

# =============================================================================
# VENV PATH HELPERS
# =============================================================================
# Centralized functions to get venv paths - use these instead of hardcoding

# Detect whether we can safely use a preferred venv path. This returns success
# when the directory already exists or the parent directory is writable so we
# could create it (e.g. /opt inside our Docker image when running as root).
_venv_path_is_usable() {
  local path="$1"
  if [ -z "${path}" ]; then
    return 1
  fi
  if [ -d "${path}" ]; then
    return 0
  fi
  if [ -e "${path}" ]; then
    return 1
  fi
  local parent
  parent="$(dirname "${path}")"
  if [ -d "${parent}" ] && [ -w "${parent}" ]; then
    return 0
  fi
  return 1
}

# Resolve the runtime venv directory with the following precedence:
# 1) VENV_DIR env var (explicit override)
# 2) Writable/pre-existing /opt/venv (Docker prebaked venv)
# 3) Repo-local .venv
get_venv_dir() {
  if [ -n "${VENV_DIR:-}" ]; then
    echo "${VENV_DIR}"
    return
  fi
  local resolved
  if _venv_path_is_usable "/opt/venv"; then
    resolved="/opt/venv"
  else
    resolved="${ROOT_DIR}/.venv"
  fi
  VENV_DIR="${resolved}"
  export VENV_DIR
  echo "${VENV_DIR}"
}

# Resolve the AWQ/llmcompressor venv directory
get_quant_venv_dir() {
  if [ -n "${QUANT_VENV_DIR:-}" ]; then
    echo "${QUANT_VENV_DIR}"
    return
  fi
  local resolved
  if _venv_path_is_usable "/opt/venv-quant"; then
    resolved="/opt/venv-quant"
  else
    resolved="${ROOT_DIR}/.venv-quant"
  fi
  QUANT_VENV_DIR="${resolved}"
  export QUANT_VENV_DIR
  echo "${QUANT_VENV_DIR}"
}

# Get the venv Python executable path
# Usage: get_venv_python
# Returns: Path to venv python binary
get_venv_python() {
  printf '%s/bin/python\n' "$(get_venv_dir)"
}

get_quant_venv_python() {
  printf '%s/bin/python\n' "$(get_quant_venv_dir)"
}

# Get the venv pip executable path
# Usage: get_venv_pip
# Returns: Path to venv pip binary
get_venv_pip() {
  printf '%s/bin/pip\n' "$(get_venv_dir)"
}

get_quant_venv_pip() {
  printf '%s/bin/pip\n' "$(get_quant_venv_dir)"
}

get_quant_python_binary() {
  if [ -n "${QUANT_PYTHON_BIN:-}" ]; then
    echo "${QUANT_PYTHON_BIN}"
    return 0
  fi
  if command -v python3.10 >/dev/null 2>&1; then
    echo "python3.10"
    return 0
  fi
  if command -v python3.11 >/dev/null 2>&1; then
    echo "python3.11"
    return 0
  fi
  get_python_binary_for_engine
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
    if command -v "python${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION}" >/dev/null 2>&1; then
      echo "python${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION}"
    elif command -v python3.10 >/dev/null 2>&1; then
      echo "python3.10"
    else
      log_err "[venv] ✗ Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION} required for TRT-LLM but not found"
      log_err "[venv] ✗ Install it first: bash scripts/steps/02_python_env.sh"
      return 1
    fi
  else
    # vLLM: use system python3
    if command -v python3 >/dev/null 2>&1; then
      echo "python3"
    elif command -v python >/dev/null 2>&1; then
      echo "python"
    else
      log_err "[venv] ✗ No Python interpreter found"
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
    if [ "${current_version}" != "${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION}" ]; then
      log_warn "[venv] ⚠ TRT requires Python ${SCRIPTS_TRT_REQUIRED_PYTHON_VERSION} but venv has ${current_version}"
      return 1
    fi
  fi
  
  return 0
}

_venv_is_protected_path() {
  case "$1" in
    /opt/venv|/opt/venv-quant) return 0 ;;
  esac
  return 1
}

_venv_remove_if_invalid() {
  local venv_path="$1"
  local engine="$2"
  local reason=""
  local venv_python="${venv_path}/bin/python"

  if [ ! -d "${venv_path}" ]; then
    return 0
  fi

  if ! validate_venv_python_version "${venv_path}"; then
    reason="incompatible Python version"
  elif [ ! -x "${venv_python}" ]; then
    reason="missing python binary"
  fi

  if [ -z "${reason}" ]; then
    return 0
  fi

  if _venv_is_protected_path "${venv_path}"; then
    log_err "[venv] ✗ ${venv_path} ${reason}; refusing to delete baked venv (${engine})"
    return 1
  fi

  log_warn "[venv] ⚠ ${venv_path} ${reason}; recreating"
  rm -rf "${venv_path}"
  return 0
}

_venv_download_get_pip() {
  local py_bin="$1"
  local tmp_file="${ROOT_DIR}/.get-pip.py"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "${tmp_file}" https://bootstrap.pypa.io/get-pip.py || true
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "${tmp_file}" https://bootstrap.pypa.io/get-pip.py || true
  fi
  if [ -f "${tmp_file}" ]; then
    "${py_bin}" "${tmp_file}" || true
    rm -f "${tmp_file}" || true
  fi
}

_venv_prepare_virtualenv_support() {
  local py_bin="$1"
  if ! "${py_bin}" -m pip --version >/dev/null 2>&1; then
    log_warn "[venv] ⚠ pip missing for ${py_bin}; bootstrapping"
    _venv_download_get_pip "${py_bin}"
  fi
  if ! "${py_bin}" -m pip install --upgrade pip >/dev/null 2>&1; then
    log_warn "[venv] ⚠ Failed to upgrade pip; continuing"
  fi
  if "${py_bin}" -m pip install virtualenv >/dev/null 2>&1; then
    return 0
  fi
  log_warn "[venv] ⚠ virtualenv install failed via pip. Attempting OS package"
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
}

_venv_create_with_virtualenv() {
  local py_bin="$1"
  local venv_path="$2"
  if "${py_bin}" -m virtualenv --version >/dev/null 2>&1; then
    "${py_bin}" -m virtualenv "${venv_path}"
    return $?
  fi
  if command -v virtualenv >/dev/null 2>&1; then
    virtualenv -p "${py_bin}" "${venv_path}"
    return $?
  fi
  return 1
}

_venv_create_new_with_python() {
  local venv_path="$1"
  local py_bin="$2"

  log_info "[venv] Creating virtual environment at ${venv_path}..."
  if "${py_bin}" -m venv "${venv_path}" >/dev/null 2>&1; then
    return 0
  fi

  log_warn "[venv] ⚠ python venv failed (ensurepip missing?). Trying virtualenv."
  _venv_prepare_virtualenv_support "${py_bin}"
  if _venv_create_with_virtualenv "${py_bin}" "${venv_path}"; then
    return 0
  fi

  log_err "[venv] ✗ Failed to create a virtual environment. Install python3-venv or virtualenv and retry."
  return 1
}

ensure_virtualenv() {
  local requested_path="${1:-}"
  local py_bin_override="${2:-}"
  local venv_path
  if [ -n "${requested_path}" ]; then
    venv_path="${requested_path}"
  else
    venv_path="$(get_venv_dir)"
    export VENV_DIR="${venv_path}"
  fi

  local engine="${INFERENCE_ENGINE:-vllm}"
  if [ -d "${venv_path}" ]; then
    _venv_remove_if_invalid "${venv_path}" "${engine}" || return 1
  fi

  if [ ! -d "${venv_path}" ]; then
    local py_bin="${py_bin_override}" 
    if [ -z "${py_bin}" ]; then
      py_bin="$(get_python_binary_for_engine)" || return 1
    fi
    _venv_create_new_with_python "${venv_path}" "${py_bin}" || return 1
  fi
}

ensure_pip_in_venv() {
  local requested_path="${1:-}"
  local venv_path
  if [ -n "${requested_path}" ]; then
    venv_path="${requested_path}"
  else
    venv_path="$(get_venv_dir)"
    export VENV_DIR="${venv_path}"
  fi

  local venv_python="${venv_path}/bin/python"
  if [ ! -x "${venv_python}" ]; then
    log_err "[venv] ✗ Virtual environment missing python binary; run ensure_virtualenv first."
    return 1
  fi

  if ! "${venv_python}" -m pip --version >/dev/null 2>&1; then
    log_warn "[venv] ⚠ pip missing in virtual environment; bootstrapping pip."
    if ! "${venv_python}" -m ensurepip --upgrade >/dev/null 2>&1; then
      _venv_download_get_pip "${venv_python}"
    fi
  fi

  if "${venv_python}" -m pip --version >/dev/null 2>&1; then
    pip_quiet_exec "${venv_python}" -m pip install --upgrade pip || true
  else
    log_err "[venv] ✗ pip is not available in the virtual environment; please install python3-venv or virtualenv and retry."
    return 1
  fi
}

# Activate virtual environment
# Usage: activate_venv [venv_dir] [fail_on_error]
#   venv_dir: Path to venv directory (defaults to ${ROOT_DIR}/.venv)
#   fail_on_error: If 1, exit on error; if 0, return error code (default: 1)
# Returns: 0 on success, 1 on failure
activate_venv() {
  local venv_dir="${1:-$(get_venv_dir)}"
  local fail_on_error="${2:-1}"
  
  if [ ! -d "${venv_dir}" ]; then
    log_err "[venv] ✗ Virtual environment not found at ${venv_dir}"
    if [ "${fail_on_error}" = "1" ]; then
      exit 1
    fi
    return 1
  fi
  
  if [ ! -f "${venv_dir}/bin/activate" ]; then
    log_err "[venv] ✗ Virtual environment corrupted (no activate script) at ${venv_dir}"
    if [ "${fail_on_error}" = "1" ]; then
      exit 1
    fi
    return 1
  fi
  
  # shellcheck disable=SC1091
  source "${venv_dir}/bin/activate" || {
    log_err "[venv] ✗ Failed to activate virtual environment at ${venv_dir}"
    if [ "${fail_on_error}" = "1" ]; then
      exit 1
    fi
    return 1
  }
  
  return 0
}
