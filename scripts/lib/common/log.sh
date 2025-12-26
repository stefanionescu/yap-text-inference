#!/usr/bin/env bash

# Logging helpers (prefix-based, no timestamps)
# Usage: log_info "[prefix] message" or log_warn "[prefix] message"

log_info() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
log_warn() { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }
log_err()  { [ -z "$*" ] && echo >&2 || echo "$*" >&2; }

