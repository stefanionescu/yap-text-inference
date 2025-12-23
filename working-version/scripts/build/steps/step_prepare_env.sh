#!/usr/bin/env bash
set -euo pipefail

source "scripts/lib/common.sh"
load_env_if_present
load_environment
source "scripts/build/helpers.sh"

echo "[build:env] Validating build environment..."

require_env HF_TOKEN

VENV_DIR="${VENV_DIR:-$PWD/.venv}"
if [ ! -d "$VENV_DIR" ]; then
  echo "[build:env] ERROR: Virtual environment not found at $VENV_DIR" >&2
  echo "[build:env] Run scripts/steps/01-install-trt.sh first" >&2
  exit 1
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "[build:env] ERROR: nvidia-smi not detected. GPU required for engine build." >&2
  exit 1
fi

echo "[build:env] Activating virtual environment..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[build:env] Configuring Hugging Face auth..."
_setup_huggingface_auth

echo "[build:env] Environment OK"
