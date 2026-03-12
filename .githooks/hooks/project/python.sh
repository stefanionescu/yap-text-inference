#!/usr/bin/env bash
# Project Python hook for full-repo Python linting on commit.
set -euo pipefail
ROOT_DIR="$(git rev-parse --show-toplevel)"
# shellcheck disable=SC1091  # lint:justify -- reason: sourced relative hook runtime helper for mode parsing -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/runtime.sh"

mode="$(parse_hook_mode "${1:-commit}")"
if [[ ${mode} != "commit" ]]; then
  die_hook_error "unsupported project hook stage: python:${mode}"
fi

cd "${ROOT_DIR}"
bash linting/lint.sh --only code
