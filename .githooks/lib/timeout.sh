#!/usr/bin/env bash
# Timeout helpers for git hook commands.

# run_with_timeout - Run a command with timeout, falling back to direct execution.
run_with_timeout() {
  local seconds="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "${seconds}" "$@"
  elif command -v gtimeout >/dev/null 2>&1; then
    gtimeout "${seconds}" "$@"
  else
    "$@"
  fi
}
