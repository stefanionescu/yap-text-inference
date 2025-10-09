#!/usr/bin/env bash

# Simple logging utility for Docker scripts
log_info() {
    echo "[INFO] $(date -Iseconds) $1"
}

log_warn() {
    echo "[WARN] $(date -Iseconds) $1" >&2
}

log_error() {
    echo "[ERROR] $(date -Iseconds) $1" >&2
}
