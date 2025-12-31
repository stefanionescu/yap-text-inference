#!/usr/bin/env bash
# Shared logging utilities for Docker scripts.
#
# Provides consistent log output formatting across TRT and vLLM build/runtime
# scripts. Uses prefix-based logging where emoji are placed in the message
# itself (e.g., log_warn "[build] ⚠ message").

log_info() { echo "$*"; }
log_warn() { echo "$*" >&2; }
log_error() { echo "$*" >&2; }
log_success() { echo "$*"; }

