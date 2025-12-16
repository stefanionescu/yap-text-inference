#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
export ROOT_DIR

# Lightweight logging helpers
log_info() { echo "[restart] $*"; }
log_warn() { echo "[restart] WARN: $*"; }
log_error() { echo "[restart] ERROR: $*" 1>&2; }

# Common helpers and env
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"
load_env_if_present
load_environment

# Restart helpers
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/restart/args.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/restart/detect.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/restart/env.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/restart/launch.sh"

usage() {
  cat <<'EOF'
Usage:
  custom/restart.sh [--install-deps]

Purpose:
  Quick restart using existing engines/models without deleting caches.

Flags:
  --install-deps   Reinstall/ensure Python deps before starting (default: off)

Behavior:
  • Stops server (light clean - preserves models/deps)
  • Auto-detects TensorRT-LLM engine directory and quantization
  • Starts server using existing engine; no re-download or rebuild

Environment:
  TRTLLM_ENGINE_DIR   Preferred engine directory (auto-detected if unset)
  HF_TOKEN            Hugging Face token (required for deps install script)
EOF
}

if ! restart_parse_args "$@"; then
  usage
  exit 1
fi

# Early validation: require HF_TOKEN before any action
if ! require_env "HF_TOKEN"; then
  exit 1
fi

log_info "Quick restart using existing models and dependencies"

log_info "Stopping server (preserving models and dependencies)..."
"${SCRIPT_DIR}/stop.sh"

restart_detect_engine || {
  log_error "Failed to detect a valid TensorRT-LLM engine directory."
  log_error "Set TRTLLM_ENGINE_DIR or run build: bash custom/02-build.sh"
  exit 1
}

restart_apply_env_and_deps || exit 1

restart_server_background
