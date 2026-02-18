#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Virtual Environment Creation + Activation Helpers
# =============================================================================
# Sourced by scripts/lib/deps/venv/main.sh after runtime/path helpers are loaded.

_venv_is_protected_path() {
  case "$1" in
    /opt/venv | /opt/venv-quant) return 0 ;;
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
