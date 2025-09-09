#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Following server logs (Ctrl+C to exit log tail)"
cd "${ROOT_DIR}"

# Wait a moment for log file to be created
sleep 2

if [ -f "${ROOT_DIR}/server.log" ]; then
  tail -f "${ROOT_DIR}/server.log"
else
  log_warn "server.log not found; server may not have started yet"
  exit 1
fi
