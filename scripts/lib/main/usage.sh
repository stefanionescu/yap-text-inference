#!/usr/bin/env bash
# =============================================================================
# Main Script Usage Documentation
# =============================================================================
# Prints command-line usage and examples for scripts/main.sh.

_MAIN_USAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/messages/main.sh
source "${_MAIN_USAGE_DIR}/../../config/messages/main.sh"

show_usage() {
  local line
  for line in "${CFG_MAIN_USAGE_LINES[@]}"; do
    printf '%s\n' "${line//\$0/$0}"
  done
  exit 1
}
