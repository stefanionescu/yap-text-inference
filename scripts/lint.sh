#!/usr/bin/env bash
# =============================================================================
# Linting Script
# =============================================================================
# Runs isort (import sorting), Ruff (Python), and ShellCheck (Bash) on the codebase.
#
# Usage: bash scripts/lint.sh [--fix]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

command -v ruff >/dev/null 2>&1 || {
    echo "ruff is not installed. Install dev deps with 'pip install -r requirements-dev.txt'." >&2
    exit 1
}

command -v isort >/dev/null 2>&1 || {
    echo "isort is not installed. Install dev deps with 'pip install -r requirements-dev.txt'." >&2
    exit 1
}

command -v shellcheck >/dev/null 2>&1 || {
    echo "shellcheck is not installed. Install dev deps with 'pip install -r requirements-dev.txt' or your package manager." >&2
    exit 1
}

PYTHON_TARGETS=()
for path in src tests docker; do
    if [[ -d "${path}" ]]; then
        PYTHON_TARGETS+=("${path}")
    fi
done

FIX_MODE=false
RUFF_ARGS=()
for arg in "$@"; do
    if [[ "${arg}" == "--fix" ]]; then
        FIX_MODE=true
    fi
    RUFF_ARGS+=("${arg}")
done

if (( ${#PYTHON_TARGETS[@]} )); then
    echo "➤ Running isort on: ${PYTHON_TARGETS[*]}"
    if ${FIX_MODE}; then
        isort "${PYTHON_TARGETS[@]}"
    else
        isort --check-only --diff "${PYTHON_TARGETS[@]}"
    fi

    echo "➤ Running Ruff on: ${PYTHON_TARGETS[*]}"
    if (( ${#RUFF_ARGS[@]} )); then
        ruff check "${PYTHON_TARGETS[@]}" "${RUFF_ARGS[@]}"
    else
        ruff check "${PYTHON_TARGETS[@]}"
    fi
else
    echo "No Python sources found to lint."
fi

if (( BASH_VERSINFO[0] >= 4 )); then
    mapfile -t SHELL_FILES < <(git ls-files '*.sh')
else
    SHELL_FILES=()
    while IFS= read -r line; do
        SHELL_FILES+=("$line")
    done < <(git ls-files '*.sh')
fi

if (( ${#SHELL_FILES[@]} )); then
    echo "➤ Running ShellCheck on tracked shell scripts"
    shellcheck --shell=bash --external-sources --severity=style --exclude=SC1090,SC1091 "${SHELL_FILES[@]}"
else
    echo "No shell scripts found to lint."
fi

echo "Linting complete."

