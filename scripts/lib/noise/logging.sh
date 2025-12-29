#!/usr/bin/env bash

# Helpers for filtering noisy server logs (e.g., warmup websocket chatter).

_noise_is_warmup_running() {
  local lock_file="${1:-}"
  if [ -z "${lock_file}" ] || [ ! -f "${lock_file}" ]; then
    return 1
  fi

  local pid=""
  if ! pid="$(tr -d '[:space:]' <"${lock_file}" 2>/dev/null)"; then
    pid=""
  fi

  if [ -z "${pid}" ]; then
    return 0
  fi

  if ps -p "${pid}" >/dev/null 2>&1; then
    return 0
  fi

  return 1
}

noise_follow_server_logs() {
  local log_file="${1:-}"
  local warmup_lock="${2:-}"
  local capture_file="${3:-}"

  if [ -z "${log_file}" ]; then
    echo "[noise] log file is required" >&2
    return 1
  fi

  touch "${log_file}" 2>/dev/null || true

  local capture_enabled=0
  if [ -n "${capture_file}" ]; then
    capture_enabled=1
    mkdir -p "$(dirname "${capture_file}")"
  fi

  local warmup_active=0
  local capture_announced=0

  tail -n +1 -F "${log_file}" | while IFS= read -r line || [ -n "${line}" ]; do
    if _noise_is_warmup_running "${warmup_lock}"; then
      if [ "${warmup_active}" -eq 0 ]; then
        warmup_active=1
        capture_announced=1
        if [ "${capture_enabled}" -eq 1 ]; then
          printf '===== Warmup run started at %s =====\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" >> "${capture_file}"
          printf '[warmup] Capturing server logs for warmup → %s\n' "${capture_file}"
        else
          printf '[warmup] Capturing server logs for warmup...\n'
        fi
      fi

      if [[ "${line}" == *"[warmup]"* ]]; then
        printf '%s\n' "${line}"
      elif [ "${capture_enabled}" -eq 1 ]; then
        printf '%s\n' "${line}" >> "${capture_file}"
      fi
      continue
    fi

    if [ "${warmup_active}" -eq 1 ]; then
      warmup_active=0
      if [ "${capture_announced}" -eq 1 ]; then
        if [ "${capture_enabled}" -eq 1 ]; then
          printf '[warmup] Warmup server logs saved to %s\n' "${capture_file}"
        else
          printf '[warmup] Warmup server log capture complete.\n'
        fi
        capture_announced=0
      fi
    fi

    printf '%s\n' "${line}"
  done
}
