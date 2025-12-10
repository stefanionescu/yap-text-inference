#!/usr/bin/env bash
set -euo pipefail

# Run screenshot intent classifier training (ModernBERT by default).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv_classifier"
PYTHON_BIN="${PYTHON_BIN:-python}"

if [ ! -d "$VENV_DIR" ]; then
  echo "[classifier] Virtualenv not found at $VENV_DIR"
  echo "[classifier] Run classifier/install.sh first."
  exit 1
fi

# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

cd "$ROOT_DIR"
"$PYTHON_BIN" -m classifier.train "$@"
