#!/usr/bin/env bash
# Shared logging utilities for Docker scripts.
#
# Provides consistent log output formatting across TRT and vLLM build/runtime
# scripts. Aligns with scripts/lib/common/log.sh naming conventions.

log_info() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
log_warn() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
log_err() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
log_success() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }

log_blank() { echo >&2; }
log_section() {
  log_blank
  log_info "$@"
}
