#!/usr/bin/env bash
# Project security hook for push-time full repository security scans.
set -euo pipefail
ROOT_DIR="$(git rev-parse --show-toplevel)"
# shellcheck disable=SC1091  # lint:justify -- reason: sourced relative hook runtime helper for mode parsing -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/runtime.sh"

mode="$(parse_hook_mode "${1:---mode=push}")"
if [[ ${mode} != "push" ]]; then
  die_hook_error "unsupported project hook stage: security:${mode}"
fi

cd "${ROOT_DIR}"
ENABLE_TRIVY="${ENABLE_TRIVY:-0}" bash linting/security/run.sh
