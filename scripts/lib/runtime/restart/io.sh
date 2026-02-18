#!/usr/bin/env bash
# =============================================================================
# Restart Guard - Snapshot/PID I/O
# =============================================================================
# PID file bookkeeping and last-config snapshot reads.

_runtime_guard_pid_file() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  printf '%s/%s' "${root_dir}" "${CFG_RUNTIME_SERVER_PID_FILE}"
}

_runtime_guard_last_config_file() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  printf '%s/%s' "${root_dir}" "${CFG_RUNTIME_LAST_CONFIG_FILE}"
}

get_running_server_pid() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  local pid_file
  pid_file="$(_runtime_guard_pid_file "${root_dir}")"

  # Treat the PID file as best-effort bookkeeping: only return the PID if the
  # process is still alive, otherwise drop the stale file so a fresh launch can
  # claim it.
  if [ -f "${pid_file}" ]; then
    local existing_pid
    existing_pid="$(cat "${pid_file}" 2>/dev/null || true)"
    if [ -n "${existing_pid}" ] && ps -p "${existing_pid}" >/dev/null 2>&1; then
      printf '%s' "${existing_pid}"
      return 0
    fi
    log_warn "[server] ⚠ Found stale ${CFG_RUNTIME_SERVER_PID_FILE} entry; removing ${pid_file}"
    rm -f "${pid_file}" || true
  fi
  return 1
}

read_last_config_value() {
  local key="$1"
  local root_dir="${2:-${ROOT_DIR:-}}"
  local config_file
  config_file="$(_runtime_guard_last_config_file "${root_dir}")"

  if [ -f "${config_file}" ]; then
    local line
    line="$(grep -E "^${key}=" "${config_file}" 2>/dev/null || true)"
    if [ -n "${line}" ]; then
      echo "${line#*=}"
    fi
  fi
}
