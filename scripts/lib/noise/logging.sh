#!/usr/bin/env bash
# =============================================================================
# Log Noise Filtering
# =============================================================================
# Helpers for filtering noisy server logs during warmup (e.g., websocket
# connection messages) while preserving important diagnostic output.

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

  local capture_active=0
  local capture_announced=0
  local warmup_filter_active=0
  local warmup_last_line_ts=0
  local warmup_grace_secs=120

  tail -n +1 -F "${log_file}" | while IFS= read -r line || [ -n "${line}" ]; do
    local lock_active=0
    if _noise_is_warmup_running "${warmup_lock}"; then
      lock_active=1
      warmup_filter_active=1
    fi

    if [ "${warmup_filter_active}" -eq 1 ] && [ "${lock_active}" -eq 0 ] && [ "${warmup_grace_secs}" -gt 0 ] && [ "${warmup_last_line_ts}" -gt 0 ]; then
      local now
      now=$(date +%s 2>/dev/null || printf '0')
      local age=$((now - warmup_last_line_ts))
      if [ "${age}" -ge "${warmup_grace_secs}" ]; then
        warmup_filter_active=0
      fi
    fi

    if [ "${warmup_filter_active}" -eq 1 ]; then
      if [ "${capture_active}" -eq 0 ]; then
        capture_active=1
        capture_announced=1
        warmup_last_line_ts=$(date +%s 2>/dev/null || printf '0')
        if [ "${capture_enabled}" -eq 1 ]; then
          printf '===== Warmup run started at %s =====\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" >>"${capture_file}"
        fi
      fi

      if [[ ${line} == *'[warmup]'* ]]; then
        printf '%s\n' "${line}"
        warmup_last_line_ts=$(date +%s 2>/dev/null || printf '0')
        if [[ ${line} == *'[warmup] ✓ Warmup + bench complete.'* ]] ||
          [[ ${line} == *'[warmup] Warmup finished with failures.'* ]] ||
          [[ ${line} == *'[warmup] ✗'* ]]; then
          warmup_filter_active=0
        fi
      elif [ "${capture_enabled}" -eq 1 ]; then
        printf '%s\n' "${line}" >>"${capture_file}"
      fi
      continue
    fi

    if [ "${capture_active}" -eq 1 ]; then
      capture_active=0
      if [ "${capture_announced}" -eq 1 ]; then
        if [ "${capture_enabled}" -eq 1 ]; then
          printf '===== Warmup run finished at %s =====\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" >>"${capture_file}"
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
