#!/usr/bin/env bash
# Global hook lint checks for full-repo commit-time docs and wording hygiene.
set -euo pipefail
ROOT_DIR="$(git rev-parse --show-toplevel)"
# shellcheck disable=SC1091  # lint:justify -- reason: sourced relative hook runtime helper for mode parsing -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/runtime.sh"

mode="$(parse_hook_mode "${1:-commit}")"
if [[ ${mode} != "commit" ]]; then
  die_hook_error "unsupported global hook stage: lint:${mode}"
fi

cd "${ROOT_DIR}"
bash linting/docs/run.sh
