#!/usr/bin/env bash
# Project coverage hook for opt-in push-time pytest coverage artifact generation.
set -euo pipefail
ROOT_DIR="$(git rev-parse --show-toplevel)"
# shellcheck disable=SC1091  # lint:justify -- reason: sourced relative hook runtime helper for mode parsing -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/runtime.sh"
# shellcheck disable=SC1091  # lint:justify -- reason: coverage uses the repo-managed Python environment for pytest execution -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/env.sh"

mode="$(parse_hook_mode "${1:---mode=push}")"
if [[ ${mode} != "push" ]]; then
  die_hook_error "unsupported project hook stage: coverage:${mode}"
fi
if [[ ${RUN_COVERAGE:-0} != "1" ]]; then
  echo "skip"
  exit 0
fi

cd "${ROOT_DIR}"
bash scripts/coverage.sh
