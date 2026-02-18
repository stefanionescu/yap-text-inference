#!/usr/bin/env bash
# =============================================================================
# Warmup Process Management
# =============================================================================
# Helpers for managing warmup process lifecycle including stopping existing
# warmup processes and cleaning up stale lock files.

_COMMON_WARMUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/runtime.sh
source "${_COMMON_WARMUP_DIR}/../../config/values/runtime.sh"

stop_existing_warmup_processes() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  if [ -z "${root_dir}" ]; then
    log_warn "[warmup] ⚠ stop_existing_warmup_processes: ROOT_DIR not set"
    return 1
  fi

  local lock_file="${root_dir}/${CFG_RUNTIME_WARMUP_LOCK_FILE}"

  if [ ! -f "${lock_file}" ]; then
    return 0 # No lock file, nothing to stop
  fi

  local existing_pid
  existing_pid="$(cat "${lock_file}" 2>/dev/null || true)"

  if [ -z "${existing_pid}" ]; then
    # Stale lock file with no PID
    log_info "[warmup] Removing stale warmup lock file (no PID)"
    rm -f "${lock_file}" || true
    return 0
  fi

  if ps -p "${existing_pid}" >/dev/null 2>&1; then
    log_info "[warmup] Stopping existing warmup process..."
    # Try graceful termination first
    kill -TERM "${existing_pid}" 2>/dev/null || true
    # Wait up to 5 seconds for graceful shutdown
    local count=0
    while [ $count -lt 5 ]; do
      if ! ps -p "${existing_pid}" >/dev/null 2>&1; then
        break
      fi
      sleep 1
      count=$((count + 1))
    done
    # Force kill if still running
    if ps -p "${existing_pid}" >/dev/null 2>&1; then
      log_warn "[warmup] ⚠ Warmup process ${existing_pid} did not terminate gracefully, forcing kill"
      kill -KILL "${existing_pid}" 2>/dev/null || true
      sleep 1
    fi
    log_info "[warmup] Warmup process stopped"
  else
    log_info "[warmup] Removing stale warmup lock file (PID ${existing_pid} not running)"
  fi

  # Clean up lock file
  rm -f "${lock_file}" || true
  return 0
}
