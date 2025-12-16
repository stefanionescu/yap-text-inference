#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
RUN_FIX=0
ONLY=""

usage() {
  cat <<'USAGE'
Usage: custom/lint.sh [--fix] [--only python|shell]

Runs linters across the repository:
  - Python: ruff (lint + format), mypy (type check)
  - Shell:  shellcheck (lint), shfmt (format if available)

Options:
  --fix              Apply auto-fixes (ruff format/check --fix, shfmt -w)
  --only python      Run only Python linters
  --only shell       Run only shell linters
  -h, --help         Show this help

Install dev tools:
  python -m pip install -r requirements-dev.txt

Shell formatting (optional):
  Install shfmt to enable shell formatting in --fix mode.
  macOS:  brew install shfmt
  Linux:  see https://github.com/mvdan/sh#shfmt for install options
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fix)
      RUN_FIX=1
      shift
      ;;
    --only)
      ONLY=${2:-}
      if [[ -z $ONLY || ($ONLY != "python" && $ONLY != "shell") ]]; then
        echo "Error: --only expects 'python' or 'shell'" >&2
        exit 2
      fi
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

have() { command -v "$1" >/dev/null 2>&1; }

header() { printf "\n==== %s ====%s\n" "$1" ""; }

run_python() {
  header "Python: ruff formatter"
  if ! python -m ruff --version >/dev/null 2>&1; then
    echo "ruff not found. Install dev deps: python -m pip install -r requirements-dev.txt" >&2
    exit 1
  fi

  if [[ $RUN_FIX -eq 1 ]]; then
    python -m ruff format "$ROOT_DIR"
  else
    python -m ruff format --check "$ROOT_DIR"
  fi

  header "Python: ruff lint"
  if [[ $RUN_FIX -eq 1 ]]; then
    python -m ruff check --fix "$ROOT_DIR"
  else
    python -m ruff check "$ROOT_DIR"
  fi

  if python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('mypy') else 1)"; then
    header "Python: mypy type check"
    PY_DIRS=()
    [[ -d "$ROOT_DIR/server" ]] && PY_DIRS+=("$ROOT_DIR/server")
    [[ -d "$ROOT_DIR/tests" ]] && PY_DIRS+=("$ROOT_DIR/tests")
    if [[ ${#PY_DIRS[@]} -gt 0 ]]; then
      python -m mypy "${PY_DIRS[@]}"
    else
      echo "No Python packages to type-check. Skipping mypy."
    fi
  else
    echo "mypy not installed; skipping type checks. Install dev deps to enable."
  fi
}

run_shell() {
  header "Shell: shellcheck"
  # Prefer git-tracked files; fallback to find. Avoid bash 4+ mapfile for macOS compatibility.
  TMP_LIST="$(mktemp)"
  git -C "$ROOT_DIR" ls-files -z "*.sh" >"$TMP_LIST" 2>/dev/null || true
  if [[ ! -s $TMP_LIST ]]; then
    find "$ROOT_DIR" -type f -name "*.sh" -print0 >"$TMP_LIST"
  fi

  if [[ ! -s $TMP_LIST ]]; then
    echo "No shell scripts found."
  else
    if ! have shellcheck; then
      echo "shellcheck not found. Install dev deps: python -m pip install -r requirements-dev.txt" >&2
      rm -f "$TMP_LIST"
      exit 1
    fi
    xargs -0 -n1 shellcheck -x <"$TMP_LIST"
  fi

  if have shfmt; then
    header "Shell: shfmt"
    if [[ $RUN_FIX -eq 1 ]]; then
      xargs -0 shfmt -w -i 2 -ci -s <"$TMP_LIST"
    else
      # -d outputs unified diff if formatting differs
      xargs -0 shfmt -d -i 2 -ci -s <"$TMP_LIST"
    fi
  else
    echo "shfmt not found; skipping shell formatting. Install via 'brew install shfmt' or your package manager."
  fi

  rm -f "$TMP_LIST"
}

case "$ONLY" in
  python)
    run_python
    ;;
  shell)
    run_shell
    ;;
  "")
    run_python
    run_shell
    ;;
esac

printf "\nAll lint checks completed successfully.\n"
