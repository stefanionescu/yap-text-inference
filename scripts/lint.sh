#!/usr/bin/env bash
# =============================================================================
# Linting Script
# =============================================================================
# Runs isort, Ruff, mypy (if installed), naming checks, and ShellCheck on the codebase.
#
# Usage: bash scripts/lint.sh [--fix]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

command -v python >/dev/null 2>&1 || {
  echo "python is required to run linting." >&2
  exit 1
}

PYTHON_TARGETS=()
for path in src tests docker; do
  if [[ -d ${path} ]]; then
    PYTHON_TARGETS+=("${path}")
  fi
done

FIX_MODE=false
for arg in "$@"; do
  if [[ ${arg} == "--fix" ]]; then
    FIX_MODE=true
  fi
done

run_quiet() {
  local label="$1"
  shift
  local tmp
  tmp="$(mktemp)"
  if "$@" >"$tmp" 2>&1; then
    rm -f "$tmp"
    return 0
  fi
  echo "[lint] ${label} failed" >&2
  cat "$tmp" >&2
  rm -f "$tmp"
  return 1
}

if ((${#PYTHON_TARGETS[@]})); then
  if ${FIX_MODE}; then
    run_quiet "isort" python -m isort --settings-path pyproject.toml "${PYTHON_TARGETS[@]}"
  else
    run_quiet "isort" python -m isort --settings-path pyproject.toml --check-only --diff "${PYTHON_TARGETS[@]}"
  fi

  if ${FIX_MODE}; then
    run_quiet "ruff format" python -m ruff format --config pyproject.toml "${PYTHON_TARGETS[@]}"
  else
    run_quiet "ruff format" python -m ruff format --config pyproject.toml --check "${PYTHON_TARGETS[@]}"
  fi

  if ${FIX_MODE}; then
    run_quiet "ruff lint" python -m ruff check --config pyproject.toml --fix "${PYTHON_TARGETS[@]}"
  else
    run_quiet "ruff lint" python -m ruff check --config pyproject.toml "${PYTHON_TARGETS[@]}"
  fi

  if python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('mypy') else 1)"; then
    run_quiet "mypy" python -m mypy "${PYTHON_TARGETS[@]}" --config-file pyproject.toml
  fi

  run_quiet "checknames" python scripts/checknames.py
fi

if ((BASH_VERSINFO[0] >= 4)); then
  mapfile -t SHELL_FILES < <(git ls-files '*.sh')
else
  SHELL_FILES=()
  while IFS= read -r line; do
    SHELL_FILES+=("$line")
  done < <(git ls-files '*.sh')
fi

if ((${#SHELL_FILES[@]})); then
  if ! command -v shellcheck >/dev/null 2>&1; then
    echo "shellcheck is not installed. Install dev deps with 'pip install -r requirements-dev.txt' or your package manager." >&2
    exit 1
  fi
  run_quiet "shellcheck" shellcheck --shell=bash --external-sources --severity=style --exclude=SC1090,SC1091 "${SHELL_FILES[@]}"

  if command -v shfmt >/dev/null 2>&1; then
    if ${FIX_MODE}; then
      run_quiet "shfmt" shfmt -w -i 2 -ci -s "${SHELL_FILES[@]}"
    else
      run_quiet "shfmt" shfmt -d -i 2 -ci -s "${SHELL_FILES[@]}"
    fi
  fi
fi
