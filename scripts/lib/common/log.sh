#!/usr/bin/env bash

# Logging helpers (prefix-based, no timestamps)
# Usage: log_info "[prefix] message" or log_warn "[prefix] message"

log_info() { echo "$*" >&2; }
log_warn() { echo "$* ⚠" >&2; }
log_err()  { echo "$* ✗" >&2; }

# Back-compat alias used by some scripts
log_error() { log_err "$@"; }

