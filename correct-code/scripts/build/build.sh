#!/usr/bin/env bash
# =============================================================================
# TensorRT-LLM Engine Build Script
# =============================================================================
# Builds optimized TensorRT-LLM engine for Orpheus 3B TTS model with:
# - INT4-AWQ weight quantization [default ORPHEUS_PRECISION_MODE=quantized]
# - FP8 on Ada/Hopper, full precision on Ampere [ORPHEUS_PRECISION_MODE=base]
# - Optimized for realtime TTS workload (60 input, 1162 output tokens)
#
# Usage: ORPHEUS_PRECISION_MODE=base bash scripts/build/build.sh [--force]
# Environment: Requires HF_TOKEN, VENV_DIR, optionally TRTLLM_ENGINE_DIR
# =============================================================================

set -euo pipefail

# Load common utilities and environment
source "scripts/lib/common.sh"
load_env_if_present
load_environment
source "scripts/build/helpers.sh"

echo ""
echo "[build] TensorRT-LLM Engine Build"

echo "[build] Validating CUDA toolkit/driver (need CUDA 13.x support)..."
if ! assert_cuda13_driver "build"; then
  echo "[build] CUDA validation failed; aborting build." >&2
  exit 1
fi

# =============================================================================
# Configuration and Argument Parsing
# =============================================================================

# Default paths and settings
VENV_DIR="${VENV_DIR:-$PWD/.venv}"
TRTLLM_REPO_DIR="${TRTLLM_REPO_DIR:-$PWD/.trtllm-repo}"
MODELS_DIR="${MODELS_DIR:-$PWD/models}"
ENGINE_OUTPUT_DIR="${TRTLLM_ENGINE_DIR:-$MODELS_DIR/orpheus-trt-awq}"

# Default configuration (matching original script)
CHECKPOINT_DIR="${CHECKPOINT_DIR:-$PWD/models/orpheus-trtllm-ckpt-int4-awq}"
PYTHON_EXEC="${PYTHON_EXEC:-python}"
PRECISION_MODE="${ORPHEUS_PRECISION_MODE:-quantized}"

usage() {
  cat <<USAGE
Usage: $0 [--force] [OPTIONS]

Options:
  --force              Rebuild even if engine exists
  --model              HF model ID or local path
  --checkpoint-dir     Checkpoint output directory
  --engine-dir         Engine output directory
  --max-batch-size     Max concurrent requests

Examples:
  $0                                    # INT4-AWQ (default)
  ORPHEUS_PRECISION_MODE=base $0        # 8-bit path
USAGE
}

# Parse command line arguments (matching original)
ARGS=()
FORCE_REBUILD=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      export MODEL_ID="$2"
      shift 2
      ;;
    --checkpoint-dir)
      CHECKPOINT_DIR="$2"
      shift 2
      ;;
    --engine-dir)
      ENGINE_OUTPUT_DIR="$2"
      shift 2
      ;;
    --dtype)
      TRTLLM_DTYPE="$2"
      shift 2
      ;;
    --max-input-len)
      export TRTLLM_MAX_INPUT_LEN="$2"
      shift 2
      ;;
    --max-output-len)
      export TRTLLM_MAX_OUTPUT_LEN="$2"
      shift 2
      ;;
    --max-batch-size)
      export TRTLLM_MAX_BATCH_SIZE="$2"
      shift 2
      ;;
    --awq-block-size)
      export AWQ_BLOCK_SIZE="$2"
      shift 2
      ;;
    --calib-size)
      export CALIB_SIZE="$2"
      shift 2
      ;;
    --force)
      FORCE_REBUILD=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done
set -- "${ARGS[@]:-}"

case "$PRECISION_MODE" in
  quantized | base) ;;
  *)
    echo "[build] ERROR: ORPHEUS_PRECISION_MODE must be 'quantized' or 'base' (got '${PRECISION_MODE}')" >&2
    exit 1
    ;;
esac

export ORPHEUS_PRECISION_MODE="$PRECISION_MODE"
export TRTLLM_DTYPE

# =============================================================================
# Environment Validation
# =============================================================================

echo "[build] Step: prepare env"
bash scripts/build/steps/step_prepare_env.sh

# =============================================================================
# Engine Build Process
# =============================================================================

echo "[build] Step: remote deploy"
bash scripts/build/steps/step_remote_deploy.sh || true

SKIP_QUANTIZATION=false
if [ -f .run/remote_result.env ]; then
  # shellcheck disable=SC1091
  source .run/remote_result.env
  case "${REMOTE_RESULT:-}" in
    10)
      if [ -f .run/engine_dir.env ]; then
        # shellcheck disable=SC1091
        source .run/engine_dir.env
      fi
      ENGINE_OUTPUT_DIR="${TRTLLM_ENGINE_DIR:-$ENGINE_OUTPUT_DIR}"
      _validate_engine || true
      echo "[build] Remote engine ready at $ENGINE_OUTPUT_DIR"
      echo "[build] Done."
      exit 0
      ;;
    11)
      SKIP_QUANTIZATION=true
      # Persisted by remote step; load it for downstream steps
      if [ -f .run/checkpoint_dir.env ]; then
        # shellcheck disable=SC1091
        source .run/checkpoint_dir.env
      fi
      if [ -n "${CHECKPOINT_DIR:-}" ]; then
        echo "[build] Using checkpoint directory: $CHECKPOINT_DIR"
      fi
      ;;
  esac
fi

# Check if rebuild is needed
if _should_skip_build; then
  echo "[build] Engine already exists at: $ENGINE_OUTPUT_DIR"
  echo "[build] Use --force to rebuild"
  # Persist for downstream scripts
  mkdir -p .run
  echo "export TRTLLM_ENGINE_DIR=\"$ENGINE_OUTPUT_DIR\"" >.run/engine_dir.env
  exit 0
fi

echo "[build] Building TensorRT-LLM engine..."
echo "[build] Output directory: $ENGINE_OUTPUT_DIR"
echo "[build] Precision mode: ${PRECISION_MODE}"

# Prepare TensorRT-LLM repo only if quantization is needed
if [[ $SKIP_QUANTIZATION != true ]]; then
  echo "[build] Step: prepare TRT-LLM repo"
  bash scripts/build/steps/step_prepare_trtllm_repo.sh
fi

echo "[build] Step: checkpoint prep"
SKIP_QUANTIZATION="$SKIP_QUANTIZATION" CHECKPOINT_DIR="$CHECKPOINT_DIR" bash scripts/build/steps/step_quantize.sh

echo "[build] Step: engine build"
CHECKPOINT_DIR="$CHECKPOINT_DIR" ENGINE_OUTPUT_DIR="$ENGINE_OUTPUT_DIR" bash scripts/build/steps/step_engine_build.sh

# step_engine_build.sh already records .run/engine_dir.env

echo ""
echo "[build] Done. Engine: ${ENGINE_OUTPUT_DIR}"
if [[ $PRECISION_MODE == "base" ]]; then
  echo "[build] Configuration: base mode (FP8 or full precision)"
else
  echo "[build] Configuration: INT4-AWQ"
fi
echo ""
echo "[build] To run server:"
echo "  export TRTLLM_ENGINE_DIR=\"${ENGINE_OUTPUT_DIR}\""
echo "  bash scripts/steps/03-run-server.sh"
echo ""

# Save build config for restart change detection
orpheus_write_build_config ".run/build_config.env"
