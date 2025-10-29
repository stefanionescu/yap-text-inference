#!/usr/bin/env bash
set -euo pipefail

timestamp() { date +"%Y-%m-%dT%H:%M:%S%z"; }

log_info() { echo "[INFO] $(timestamp) $*"; }
log_warn() { echo "[WARN] $(timestamp) $*" >&2; }
log_err()  { echo "[ERR ] $(timestamp) $*" >&2; }

# Back-compat alias used by some scripts
log_error() { log_err "$@"; }


