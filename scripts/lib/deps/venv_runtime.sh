#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Virtual Environment Runtime + Path Helpers
# =============================================================================
# Sourced by scripts/lib/deps/venv.sh after common dependencies are loaded.

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

  if [[ ${engine,,} == "trt" ]]; then
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
