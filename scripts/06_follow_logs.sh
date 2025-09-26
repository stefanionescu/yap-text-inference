#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Following server logs (Ctrl+C to exit tail — server keeps running)"
cd "${ROOT_DIR}"
sleep 2

if [ -f "${ROOT_DIR}/server.log" ]; then
  # Keep only the latest 250MB in-place (truncate older content)
  MAX_KEEP_BYTES=$((250 * 1024 * 1024))
  SZ=$(wc -c <"${ROOT_DIR}/server.log" 2>/dev/null || echo 0)
  if [ "$SZ" -gt "$MAX_KEEP_BYTES" ]; then
    OFFSET=$((SZ - MAX_KEEP_BYTES))
    TMP_FILE="${ROOT_DIR}/.server.log.trim"
    # tail -c is portable enough on GNU coreutils; fallback to dd if needed
    if tail -c "$MAX_KEEP_BYTES" "${ROOT_DIR}/server.log" > "$TMP_FILE" 2>/dev/null; then
      mv "$TMP_FILE" "${ROOT_DIR}/server.log" 2>/dev/null || true
      log_info "Trimmed server.log to latest 250MB (removed ${OFFSET} bytes)"
    else
      dd if="${ROOT_DIR}/server.log" of="$TMP_FILE" bs=1 skip="$OFFSET" status=none 2>/dev/null || true
      mv "$TMP_FILE" "${ROOT_DIR}/server.log" 2>/dev/null || true
      log_info "Trimmed server.log to latest 250MB via dd (removed ${OFFSET} bytes)"
    fi
  fi
  tail -F "${ROOT_DIR}/server.log" || true
else
  log_warn "server.log not found; server may not have started yet"
  exit 1
fi
