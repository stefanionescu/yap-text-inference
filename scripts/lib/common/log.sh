#!/usr/bin/env bash
# =============================================================================
# Logging Utilities
# =============================================================================
# Simple prefix-based logging helpers that output to stderr.
# Usage: log_info "[prefix] message" or log_warn "[prefix] message"

log_info() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
log_warn() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
log_err()  { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }

log_blank() { echo >&2; }
log_section() {
  log_blank
  log_info "$@"
}
