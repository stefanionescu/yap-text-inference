#!/usr/bin/env bash
# Shared constants for git hooks. Sourced by .githooks/lib/runtime.sh.

# shellcheck disable=SC1091  # lint:justify -- reason: hook runtime loads repo-local hook policy from linting/config -- ticket: N/A
source "${ROOT_DIR}/linting/config/repo/hooks.env"
