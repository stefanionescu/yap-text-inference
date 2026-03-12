#!/usr/bin/env bash
# Global hook security checks for commit-time repository hygiene only.
set -euo pipefail
ROOT_DIR="$(git rev-parse --show-toplevel)"
# shellcheck disable=SC1091  # lint:justify -- reason: sourced relative hook runtime helper for staged-file inspection -- ticket: N/A
source "${ROOT_DIR}/.githooks/lib/runtime.sh"

mode="$(parse_hook_mode "${1:-commit}")"
if [[ ${mode} != "commit" ]]; then
  die_hook_error "unsupported global hook stage: security:${mode}"
fi

cd "${ROOT_DIR}"
staged_envs="$(staged_files | grep -iE "${PROD_ENV_PATTERN}" || true)"
if [[ -n ${staged_envs} ]]; then
  echo "Production environment files are staged:" >&2
  echo "${staged_envs}" >&2
  echo "Remove them from the index or bypass with SKIP_ENV_CHECK=1." >&2
  exit 1
fi
