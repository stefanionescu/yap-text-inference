#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Light stop: preserving AWQ models, venv, and caches"

# Light stop - preserve everything except server process
NUKE_ALL=0 "${SCRIPT_DIR}/stop.sh"

log_info "Server stopped. AWQ models and dependencies preserved."
log_info "Quick restart: bash scripts/restart.sh"
