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

# shellcheck disable=SC1091
source "${SCRIPT_DIR}/restart/config.sh"
restart_resolve_precision_mode

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
  scripts/restart.sh [--install-deps] [--force] [--push-quant]

Smart restart with automatic rebuild on config changes.

Options:
  --install-deps    DESTRUCTIVE: Nuke venv, pip cache, MPI packages and reinstall ALL from scratch
  --force           Force rebuild even if config unchanged
  --push-quant      Push artifacts to HF after rebuild (requires validation)

Auto-Rebuild:
  Automatically rebuilds when any of these change from previous run:
  • MODEL_ID
  • MODEL_PRESET  
  • ORPHEUS_PRECISION_MODE

Dependency Caching (Default Behavior):
  By default, existing dependencies are reused if they have correct versions:
  • MPI packages (libopenmpi3, openmpi-bin, openmpi-common) - skipped if version matches
  • Python venv (.venv) - reused if exists and valid
  • PyTorch/TorchVision - skipped if correct version installed
  • TensorRT-LLM - skipped if correct version installed
  
  Wrong versions are automatically uninstalled and replaced with correct ones.
  Use --install-deps only when you need a completely clean slate.

Behavior:
  • Stops server
  • Checks if config changed → triggers rebuild if needed
  • Optionally pushes to HuggingFace (--push-quant)
  • Starts server using engine

Examples:
  scripts/restart.sh                              # Restart (reuse existing deps)
  scripts/restart.sh --install-deps               # Force reinstall ALL dependencies
  ORPHEUS_PRECISION_MODE=base scripts/restart.sh  # Switch to 8-bit (auto-rebuilds)
  MODEL_PRESET=fast scripts/restart.sh            # Switch model (auto-rebuilds)
  scripts/restart.sh --force                      # Force rebuild
  scripts/restart.sh --force --push-quant         # Force rebuild and push to HF

Environment:
  ORPHEUS_PRECISION_MODE  quantized (default) | base
  MODEL_PRESET            canopy (default) | fast
  MODEL_ID                Override model (optional)
  HF_TOKEN                Required for builds

When --push-quant is specified:
  HF_PUSH_REPO_ID         Required: target HF repo (e.g., your-org/model-trtllm)
  GPU_SM_ARCH             Required: GPU architecture (sm80, sm89, sm90)
  HF_PUSH_PRIVATE         Optional: 1=private (default), 0=public
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

# =============================================================================
# --push-quant Validation (upfront, before any heavy operations)
# =============================================================================

if [ "$PUSH_QUANT" = "1" ]; then
  bash "${SCRIPT_DIR}/build/push.sh" validate restart
fi

log_info "Validating CUDA toolkit/driver (require CUDA 13.x support)..."
if ! assert_cuda13_driver "restart"; then
  log_error "CUDA validation failed; aborting restart."
  exit 1
fi

log_info "Stopping server (preserving models and dependencies)..."
"${SCRIPT_DIR}/stop.sh"

# Check if config changed (auto-triggers rebuild)
NEEDS_REBUILD=0
if [[ "${FORCE_REBUILD:-0}" == "1" ]]; then
  log_info "Force rebuild requested via --force"
  NEEDS_REBUILD=1
elif config_changed; then
  log_info "Configuration changed from previous build - auto-triggering rebuild"
  NEEDS_REBUILD=1
fi

# Handle rebuild: delete checkpoint/engine and rebuild
if [[ "$NEEDS_REBUILD" == "1" ]]; then
  log_info "Will re-quantize and rebuild engine"
  
  # Determine paths based on precision mode
  if [[ "${ORPHEUS_PRECISION_MODE:-quantized}" == "base" ]]; then
    ckpt_dir="${CHECKPOINT_DIR:-$ROOT_DIR/models/orpheus-trtllm-ckpt-8bit}"
    engine_dir="${TRTLLM_ENGINE_DIR:-$ROOT_DIR/models/orpheus-trt-8bit}"
  else
    ckpt_dir="${CHECKPOINT_DIR:-$ROOT_DIR/models/orpheus-trtllm-ckpt-int4-awq}"
    engine_dir="${TRTLLM_ENGINE_DIR:-$ROOT_DIR/models/orpheus-trt-awq}"
  fi
  
  # Remove existing checkpoint and engine
  if [[ -d "$ckpt_dir" ]]; then
    log_info "Removing existing checkpoint: $ckpt_dir"
    rm -rf "$ckpt_dir"
  fi
  if [[ -d "$engine_dir" ]]; then
    log_info "Removing existing engine: $engine_dir"
    rm -rf "$engine_dir"
  fi
  
  # Run full build pipeline
  log_info "Running build pipeline..."
  export FORCE_REBUILD=true
  bash "${SCRIPT_DIR}/build/build.sh" || {
    log_error "Build failed"
    exit 1
  }
  
  # Save new config after successful build
  save_build_config

  # Push to HuggingFace if --push-quant was specified
  if [ "$PUSH_QUANT" = "1" ]; then
    bash "${SCRIPT_DIR}/build/push.sh" run restart || {
      log_error "HF push failed"
      exit 1
    }
  fi
fi

log_info "Quick restart using existing models and dependencies"

restart_detect_engine || {
  log_error "Failed to detect a valid TensorRT-LLM engine directory."
  log_error "Set TRTLLM_ENGINE_DIR or run build: bash scripts/steps/02-build.sh"
  exit 1
}

restart_apply_env_and_deps || exit 1

restart_server_background
