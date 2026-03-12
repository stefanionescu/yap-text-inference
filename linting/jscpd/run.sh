#!/usr/bin/env bash
# run_jscpd - Execute the repo-local jscpd binary installed by bun.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
# shellcheck source=../bootstrap.sh
source "${ROOT_DIR}/linting/bootstrap.sh"
activate_repo_tool_paths

if [[ ! -d ${ROOT_DIR}/node_modules ]]; then
  echo "error: repo JS tooling missing under ${ROOT_DIR}/node_modules" >&2
  echo "error: run bun install before using jscpd-backed quality checks" >&2
  exit 1
fi

if ! command -v bun >/dev/null 2>&1; then
  echo "error: bun is required to run repo-local jscpd" >&2
  echo "error: install Bun and ensure ~/.bun/bin is available" >&2
  exit 1
fi

exec bun x jscpd "$@"
