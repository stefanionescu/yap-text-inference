#!/usr/bin/env bash
# =============================================================================
# Logging Utilities
# =============================================================================
# Simple stderr logging helpers.
# Usage: log_info "message" or log_infof "template %s" "value"

_log_emit() {
  [ -z "$*" ] && echo >&2 || echo "$*" >&2
}

_log_emitf() {
  local template="${1:-}"
  shift || true
  if [ -z "${template}" ]; then
    echo >&2
    return 0
  fi
  # shellcheck disable=SC2059  # caller intentionally provides printf template
  printf "${template}\n" "$@" >&2
}

log_info() { _log_emit "$@"; }
log_warn() { _log_emit "$@"; }
log_err() { _log_emit "$@"; }
log_infof() { _log_emitf "$@"; }
log_warnf() { _log_emitf "$@"; }
log_errf() { _log_emitf "$@"; }

log_blank() { echo >&2; }
log_section() {
  log_blank
  log_info "$@"
}
