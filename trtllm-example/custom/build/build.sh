#!/usr/bin/env bash
# =============================================================================
# TensorRT-LLM Engine Build Script
# =============================================================================
# Builds optimized TensorRT-LLM engine for Orpheus 3B TTS model with:
# - INT4-AWQ weight quantization [default]
# - or Base weights (FP16 / FP8) with TensorRT-LLM kernels
# - Optimized for realtime TTS workload (48 input, 1162 output tokens)
#
# Usage: bash custom/build/build.sh [--force] [--max-batch-size N]
# Environment: Requires HF_TOKEN, VENV_DIR, optionally TRTLLM_ENGINE_DIR
# =============================================================================

set -euo pipefail

# Load common utilities and environment
source "custom/lib/common.sh"
load_env_if_present
load_environment "$@"
source "custom/build/helpers.sh"

echo "=== TensorRT-LLM Engine Build (orchestrator) ==="

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
Usage: $0 [--model ID_OR_PATH] [--checkpoint-dir DIR] [--engine-dir DIR] [--dtype float16|fp8_e4m3|bfloat16] [--max-input-len N] [--max-output-len N] [--max-batch-size N] [--precision-mode quantized|base] [--force]

Precision modes:
  quantized (default): HF checkpoint → INT4-AWQ checkpoint → TRT engine
  base: HF checkpoint → base TensorRT-LLM checkpoint → TRT engine

Defaults:
  --model              ${MODEL_ID}
  --checkpoint-dir     ${CHECKPOINT_DIR}
  --engine-dir         ${ENGINE_OUTPUT_DIR}
  --dtype              ${TRTLLM_DTYPE}
  --max-input-len      ${TRTLLM_MAX_INPUT_LEN}
  --max-output-len     ${TRTLLM_MAX_OUTPUT_LEN}
  --max-batch-size     ${TRTLLM_MAX_BATCH_SIZE}
  --awq-block-size     ${AWQ_BLOCK_SIZE}
  --calib-size         ${CALIB_SIZE}
USAGE
}

# Parse command line arguments (matching original)
ARGS=()
FORCE_REBUILD=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL_ID="$2"
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
      TRTLLM_MAX_INPUT_LEN="$2"
      shift 2
      ;;
    --max-output-len)
      TRTLLM_MAX_OUTPUT_LEN="$2"
      shift 2
      ;;
    --max-batch-size)
      TRTLLM_MAX_BATCH_SIZE="$2"
      shift 2
      ;;
    --awq-block-size)
      AWQ_BLOCK_SIZE="$2"
      shift 2
      ;;
    --calib-size)
      CALIB_SIZE="$2"
      shift 2
      ;;
    --precision-mode)
      PRECISION_MODE="$2"
      shift 2
      ;;
    --no-quantize)
      PRECISION_MODE="base"
      shift
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
    echo "[build] ERROR: --precision-mode must be 'quantized' or 'base' (got '${PRECISION_MODE}')" >&2
    exit 1
    ;;
esac

export ORPHEUS_PRECISION_MODE="$PRECISION_MODE"
if [[ $PRECISION_MODE == "base" ]]; then
  if [[ -n ${BASE_INFERENCE_DTYPE:-} ]]; then
    TRTLLM_DTYPE="${BASE_INFERENCE_DTYPE}"
    echo "[build] Base precision override via BASE_INFERENCE_DTYPE=${TRTLLM_DTYPE}"
  elif [[ ${ORPHEUS_TRTLLM_DTYPE_DEFAULTED:-0} == "1" ]]; then
    auto_dtype=$(_resolve_base_inference_dtype)
    if [[ -n $auto_dtype ]]; then
      TRTLLM_DTYPE="$auto_dtype"
      echo "[build] Auto-selected base inference dtype: ${TRTLLM_DTYPE}"
    fi
  else
    echo "[build] Base precision using user-provided TRTLLM_DTYPE=${TRTLLM_DTYPE}"
  fi
  gpu_name=$(_detect_gpu_name)
  if [[ -n $gpu_name ]]; then
    echo "[build] Detected GPU: ${gpu_name}"
  fi
fi
export TRTLLM_DTYPE

# =============================================================================
# Environment Validation
# =============================================================================

echo "[build] Step: prepare env"
bash custom/build/steps/step_prepare_env.sh

# =============================================================================
# Engine Build Process
# =============================================================================

echo "[build] Step: remote deploy"
bash custom/build/steps/step_remote_deploy.sh || true

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
      echo "[build] ✓ Remote engine ready at $ENGINE_OUTPUT_DIR"
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
echo "[build] Precision mode: ${PRECISION_MODE} (dtype=${TRTLLM_DTYPE})"

# Prepare TensorRT-LLM repo only if quantization is needed
if [[ $SKIP_QUANTIZATION != true ]]; then
  echo "[build] Step: prepare TRT-LLM repo"
  bash custom/build/steps/step_prepare_trtllm_repo.sh
fi

echo "[build] Step: checkpoint prep"
SKIP_QUANTIZATION="$SKIP_QUANTIZATION" CHECKPOINT_DIR="$CHECKPOINT_DIR" bash custom/build/steps/step_quantize.sh

echo "[build] Step: engine build"
CHECKPOINT_DIR="$CHECKPOINT_DIR" ENGINE_OUTPUT_DIR="$ENGINE_OUTPUT_DIR" bash custom/build/steps/step_engine_build.sh

# step_engine_build.sh already records .run/engine_dir.env

echo ""
echo "[build] ============================================"
echo "[build] Done. Engine: ${ENGINE_OUTPUT_DIR}"
if [[ $PRECISION_MODE == "base" ]]; then
  echo "[build] Configuration: Base weights (${TRTLLM_DTYPE})"
else
  echo "[build] Configuration: INT4-AWQ weight-only"
fi
echo "[build] To run server:"
echo "  export TRTLLM_ENGINE_DIR=\"${ENGINE_OUTPUT_DIR}\""
echo "  bash custom/03-run-server.sh"
echo "[build] ============================================"
