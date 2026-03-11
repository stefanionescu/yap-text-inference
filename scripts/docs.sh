#!/usr/bin/env bash
# run_docs_lint - Run markdown, typos, and banned-terms checks.

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
  echo "[docs] ${label} failed" >&2
  cat "${tmp}" >&2
  rm -f "${tmp}"
  return 1
}

cd "${ROOT_DIR}"
run_cmd "banned-terms" python linting/banned/terms.py
run_cmd "codespell" codespell \
  --ignore-words .codespellignore \
  --skip "./node_modules,./.git,./.venv,./.cache,./.mypy_cache,./.pytest_cache,./.ruff_cache,./htmlcov,./codeql-db,./tests/support/messages,./tests/support/prompts,./coverage.xml,./pytest.xml,./codeql-results.sarif,./bearer-report.json" \
  .
run_cmd "pymarkdown" python linting/pymarkdown/run.py scan
