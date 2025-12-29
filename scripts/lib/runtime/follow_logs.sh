#!/usr/bin/env bash
set -euo pipefail

# Tail server.log while suppressing noisy server entries produced by warmup traffic.
# Lines dropped during warmup are appended to a dedicated capture file so they
# can be inspected later without spamming the interactive console.

LOG_FILE="${1:-}"
WARMUP_LOCK_FILE="${2:-}"
CAPTURE_FILE="${3:-}"

if [ -z "${LOG_FILE}" ]; then
  echo "Usage: follow_logs.sh <server_log> [warmup_lock_file] [capture_file]" >&2
  exit 1
fi

touch "${LOG_FILE}" 2>/dev/null || true

capture_enabled=0
if [ -n "${CAPTURE_FILE}" ]; then
  capture_enabled=1
  mkdir -p "$(dirname "${CAPTURE_FILE}")"
fi

is_warmup_running() {
  if [ -z "${WARMUP_LOCK_FILE}" ] || [ ! -f "${WARMUP_LOCK_FILE}" ]; then
    return 1
  fi
  local pid=""
  if ! pid="$(tr -d '[:space:]' <"${WARMUP_LOCK_FILE}" 2>/dev/null)"; then
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

warmup_active=0
capture_announced=0

tail -n +1 -F "${LOG_FILE}" | while IFS= read -r line || [ -n "${line}" ]; do
  if is_warmup_running; then
    if [ "${warmup_active}" -eq 0 ]; then
      warmup_active=1
      capture_announced=1
      if [ "${capture_enabled}" -eq 1 ]; then
        printf '===== Warmup run started at %s =====\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" >> "${CAPTURE_FILE}"
        printf '[warmup] Capturing server logs for warmup → %s\n' "${CAPTURE_FILE}"
      else
        printf '[warmup] Capturing server logs for warmup...\n'
      fi
    fi
    if [[ "${line}" == *"[warmup]"* ]]; then
      printf '%s\n' "${line}"
    else
      if [ "${capture_enabled}" -eq 1 ]; then
        printf '%s\n' "${line}" >> "${CAPTURE_FILE}"
      fi
    fi
    continue
  fi

  if [ "${warmup_active}" -eq 1 ]; then
    warmup_active=0
    if [ "${capture_announced}" -eq 1 ]; then
      if [ "${capture_enabled}" -eq 1 ]; then
        printf '[warmup] Warmup server logs saved to %s\n' "${CAPTURE_FILE}"
      else
        printf '[warmup] Warmup server log capture complete.\n'
      fi
      capture_announced=0
    fi
  fi

  printf '%s\n' "${line}"
done
