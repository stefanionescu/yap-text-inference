#!/usr/bin/env bash
# shellcheck disable=SC1091
# Tool-only logging - sources shared logging utilities.
#
# This wrapper exists so runtime scripts can source logs.sh from the same
# directory without knowing about the common/ layout.

_LOGS_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find common scripts directory (works in Docker and dev contexts)
if [ -d "/app/common/scripts" ]; then
  source "/app/common/scripts/logs.sh"
elif [ -d "${_LOGS_SCRIPT_DIR}/../../common/scripts" ]; then
  source "${_LOGS_SCRIPT_DIR}/../../common/scripts/logs.sh"
else
  # Fallback logging if common not found
  log_info() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
  log_warn() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
  log_err() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
  log_success() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
  log_error() { log_err "$@"; }
fi
