#!/usr/bin/env bash

# Logging utilities for Docker scripts (prefix-based, emoji in message)
# Usage: log_info "[prefix] message" or log_warn "[prefix] ⚠ message"
# Emoji should be placed after [prefix] in the message itself

log_info() { echo "$*"; }
log_warn() { echo "$*" >&2; }
log_error() { echo "$*" >&2; }
log_success() { echo "$*"; }

