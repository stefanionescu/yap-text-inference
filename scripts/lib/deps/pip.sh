#!/usr/bin/env bash

# Shared dependency installation helpers.

deps_export_pip() {
  export PIP_ROOT_USER_ACTION=${PIP_ROOT_USER_ACTION:-ignore}
  export PIP_DISABLE_PIP_VERSION_CHECK=${PIP_DISABLE_PIP_VERSION_CHECK:-1}
  export PIP_NO_INPUT=${PIP_NO_INPUT:-1}
  export PIP_PREFER_BINARY=${PIP_PREFER_BINARY:-1}
  export PIP_PROGRESS_BAR=${PIP_PROGRESS_BAR:-off}
  export FLASHINFER_ENABLE_AOT=${FLASHINFER_ENABLE_AOT:-1}
}

_pip_quiet_log_file() {
  if [ -n "${PIP_INSTALL_LOG:-}" ]; then
    echo "${PIP_INSTALL_LOG}"
    return
  fi

  local base_dir
  base_dir="${ROOT_DIR:-$(pwd)}"
  echo "${base_dir}/logs/pip-install.log"
}

_pip_quiet_notice() {
  local level="${1:-warn}"
  shift
  local msg="$*"

  case "${level}" in
    err)
      if command -v log_err >/dev/null 2>&1; then
        log_err "${msg}"
      else
        echo "${msg}" >&2
      fi
      ;;
    *)
      if command -v log_warn >/dev/null 2>&1; then
        log_warn "${msg}"
      else
        echo "${msg}" >&2
      fi
      ;;
  esac
}

pip_quiet_exec() {
  if [ "$#" -lt 1 ]; then
    _pip_quiet_notice err "[pip] ✗ pip_quiet_exec requires a command"
    return 1
  fi

  local pip_cmd="$1"
  shift
  if [ -z "${pip_cmd}" ]; then
    _pip_quiet_notice err "[pip] ✗ pip executable not provided"
    return 1
  fi

  local tmp_log
  tmp_log="$(mktemp -t pip-quiet-XXXXXX 2>/dev/null || mktemp /tmp/pip-quiet-XXXXXX)"
  if "${pip_cmd}" "$@" >"${tmp_log}" 2>&1; then
    rm -f "${tmp_log}"
    return 0
  fi

  local rc=$?
  local log_file
  log_file="$(_pip_quiet_log_file)"
  mkdir -p "$(dirname "${log_file}")" 2>/dev/null || true
  {
    echo "===== $(date -Iseconds 2>/dev/null || date)"
    printf 'pip cmd: %s' "${pip_cmd}"
    if [ "$#" -gt 0 ]; then
      printf ' %s' "$@"
    fi
    printf '\n'
    cat "${tmp_log}" || true
    echo "===== exit code: ${rc}"
  } >> "${log_file}" 2>/dev/null || true

  _pip_quiet_notice warn "[pip] ⚠ Command failed; see ${log_file} (last lines below)"
  tail -n 60 "${tmp_log}" >&2 || cat "${tmp_log}" >&2 || true
  rm -f "${tmp_log}"
  return "${rc}"
}

pip_quiet() {
  local pip_bin
  pip_bin="$(command -v pip 2>/dev/null || true)"
  if [ -z "${pip_bin}" ]; then
    _pip_quiet_notice err "[pip] ✗ pip executable not found in PATH"
    return 1
  fi
  pip_quiet_exec "${pip_bin}" "$@"
}

