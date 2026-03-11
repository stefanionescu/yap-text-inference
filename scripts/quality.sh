#!/usr/bin/env bash
# run_quality_checks - Run complexity, dependency hygiene, dead-code, and duplicate-code checks.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"

# run_cmd - Run a command and show its buffered output on failure.
run_cmd() {
  local label="$1"
  shift
  local tmp
  tmp="$(mktemp)"
  if "$@" >"${tmp}" 2>&1; then
    rm -f "${tmp}"
    return 0
  fi
  echo "[quality] ${label} failed" >&2
  cat "${tmp}" >&2
  rm -f "${tmp}"
  return 1
}

cd "${ROOT_DIR}"
run_cmd "lizard" bash linting/lizard/run.sh
run_cmd "deptry" python -m deptry --config pyproject.toml src tests
run_cmd "vulture" python -m vulture src linting --min-confidence 100
run_cmd "jscpd python" bunx jscpd --config .jscpd/python.json
run_cmd "jscpd bash" bunx jscpd --config .jscpd/bash.json
