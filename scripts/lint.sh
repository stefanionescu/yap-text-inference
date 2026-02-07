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

if ((${#PYTHON_TARGETS[@]})); then
  echo "➤ Running isort on: ${PYTHON_TARGETS[*]}"
  if ${FIX_MODE}; then
    python -m isort --settings-path pyproject.toml "${PYTHON_TARGETS[@]}"
  else
    python -m isort --settings-path pyproject.toml --check-only --diff "${PYTHON_TARGETS[@]}"
  fi

  echo "➤ Running Ruff formatter on: ${PYTHON_TARGETS[*]}"
  if ${FIX_MODE}; then
    python -m ruff format --config pyproject.toml "${PYTHON_TARGETS[@]}"
  else
    python -m ruff format --config pyproject.toml --check "${PYTHON_TARGETS[@]}"
  fi

  echo "➤ Running Ruff lint on: ${PYTHON_TARGETS[*]}"
  if ${FIX_MODE}; then
    python -m ruff check --config pyproject.toml --fix "${PYTHON_TARGETS[@]}"
  else
    python -m ruff check --config pyproject.toml "${PYTHON_TARGETS[@]}"
  fi

  if python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('mypy') else 1)"; then
    echo "➤ Running mypy on: ${PYTHON_TARGETS[*]}"
    python -m mypy "${PYTHON_TARGETS[@]}" --config-file pyproject.toml
  else
    echo "mypy not installed; skipping type checks. Install dev deps to enable."
  fi

  echo "➤ Checking Python file names"
  python scripts/checknames.py
else
  echo "No Python sources found to lint."
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
  echo "➤ Running ShellCheck on tracked shell scripts"
  if ! command -v shellcheck >/dev/null 2>&1; then
    echo "shellcheck is not installed. Install dev deps with 'pip install -r requirements-dev.txt' or your package manager." >&2
    exit 1
  fi
  shellcheck --shell=bash --external-sources --severity=style --exclude=SC1090,SC1091 "${SHELL_FILES[@]}"

  if command -v shfmt >/dev/null 2>&1; then
    echo "➤ Running shfmt on tracked shell scripts"
    if ${FIX_MODE}; then
      shfmt -w -i 2 -ci -s "${SHELL_FILES[@]}"
    else
      shfmt -d -i 2 -ci -s "${SHELL_FILES[@]}"
    fi
  else
    echo "shfmt not found; skipping shell formatting."
  fi
else
  echo "No shell scripts found to lint."
fi

echo "Linting complete."
