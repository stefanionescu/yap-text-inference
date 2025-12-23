#!/usr/bin/env bash
# =============================================================================
# Complete Setup Pipeline Script
# =============================================================================
# Runs the complete setup pipeline from system bootstrap to server startup:
# 1. System bootstrap (dependencies, CUDA check)
# 2. Python environment setup (venv, packages, TensorRT-LLM)
# 3. Engine build (quantization based on ORPHEUS_PRECISION_MODE)
# 4. Server startup (FastAPI with TTS endpoints)
#
# Usage: bash scripts/main.sh [--push-quant]
# Environment: HF_TOKEN required. Set ORPHEUS_PRECISION_MODE=base for 8-bit.
#
# Options:
#   --push-quant    Push artifacts to Hugging Face after build (requires validation)
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
export ROOT_DIR
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"
load_env_if_present
load_environment

# =============================================================================
# Argument Parsing
# =============================================================================

PUSH_QUANT=0
FORCE_INSTALL_DEPS="${FORCE_INSTALL_DEPS:-0}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --push-quant)
      PUSH_QUANT=1
      shift
      ;;
    --install-deps)
      FORCE_INSTALL_DEPS=1
      shift
      ;;
    --help | -h)
      echo "Usage: bash scripts/main.sh [--push-quant] [--install-deps]"
      echo ""
      echo "Options:"
      echo "  --push-quant    Push artifacts to Hugging Face after build"
      echo "                  Requires: HF_TOKEN, HF_PUSH_REPO_ID, GPU_SM_ARCH"
      echo "  --install-deps  Force reinstall all dependencies (nuke venv, MPI, etc.)"
      echo ""
      echo "Environment:"
      echo "  HF_TOKEN                Required for model access"
      echo "  ORPHEUS_PRECISION_MODE  quantized (default) | base"
      echo ""
      echo "Dependency Caching:"
      echo "  By default, existing dependencies are reused if they have correct versions."
      echo "  Use --install-deps to force reinstall everything from scratch."
      echo ""
      echo "When --push-quant is specified:"
      echo "  HF_TOKEN or HUGGINGFACE_HUB_TOKEN  Required with write access"
      echo "  HF_PUSH_REPO_ID                    Required target HF repo"
      echo "  GPU_SM_ARCH                        Required GPU architecture"
      echo "  HF_PUSH_PRIVATE                    Optional (1=private, 0=public, default=1)"
      exit 0
      ;;
    *)
      shift
      ;;
  esac
done

export PUSH_QUANT
export FORCE_INSTALL_DEPS

# Default precision mode if not set
export ORPHEUS_PRECISION_MODE="${ORPHEUS_PRECISION_MODE:-quantized}"

echo ""
echo "[pipeline] Complete TTS Setup"
echo "[pipeline] Precision mode: ${ORPHEUS_PRECISION_MODE}"
if [[ $ORPHEUS_PRECISION_MODE == "base" ]]; then
  echo "[pipeline] Will use base mode (FP8 on Ada/Hopper, full precision on Ampere)"
else
  echo "[pipeline] Will use INT4-AWQ quantization"
fi

# =============================================================================
# Environment Validation
# =============================================================================

# Check required environment variables
if [ -z "${HF_TOKEN:-}" ]; then
  echo "ERROR: HF_TOKEN not set. Export your HuggingFace token first." >&2
  echo 'Example: export HF_TOKEN="hf_xxx"' >&2
  exit 1
fi

# =============================================================================
# --push-quant Validation (upfront, before any heavy operations)
# =============================================================================

if [ "$PUSH_QUANT" = "1" ]; then
  bash "${SCRIPT_DIR}/build/push.sh" validate pipeline
fi

echo "[pipeline] Validating CUDA toolkit and driver (need CUDA 13.x support)..."
if ! assert_cuda13_driver "pipeline"; then
  echo "[pipeline] CUDA validation failed; aborting pipeline." >&2
  exit 1
fi

echo "[pipeline] HuggingFace token: ${HF_TOKEN:0:8}..."
if [ -n "${GPU_SM_ARCH:-}" ]; then
  echo "[pipeline] GPU architecture: ${GPU_SM_ARCH}"
else
  echo "[pipeline] GPU architecture: auto-detected"
fi

# =============================================================================
# Pipeline Execution
# =============================================================================

# Create directories for logs and runtime files
mkdir -p logs .run

# Define the complete pipeline command
# Note: ORPHEUS_PRECISION_MODE, PUSH_QUANT, and FORCE_INSTALL_DEPS are exported before this runs
# shellcheck disable=SC2016
PIPELINE_CMD='
    export ORPHEUS_PRECISION_MODE="${ORPHEUS_PRECISION_MODE:-quantized}" && \
    export FORCE_INSTALL_DEPS="${FORCE_INSTALL_DEPS:-0}" && \
    echo "" && \
    echo "[pipeline] Step 1/4: System Bootstrap" && \
    bash scripts/steps/00-bootstrap.sh && \
    echo "" && \
    echo "[pipeline] Step 2/4: Install Dependencies" && \
    bash scripts/steps/01-install-trt.sh && \
    echo "" && \
    echo "[pipeline] Step 3/4: Build TensorRT Engine (${ORPHEUS_PRECISION_MODE})" && \
    bash scripts/steps/02-build.sh && \
    echo "" && \
    if [ "${PUSH_QUANT:-0}" = "1" ]; then \
        bash scripts/build/push.sh run pipeline && \
        echo ""; \
    fi && \
    echo "[pipeline] Step 4/4: Start TTS Server" && \
    # Load engine dir produced by build/fetch step if present
    if [ -f .run/engine_dir.env ]; then \
        # shellcheck disable=SC1091
        source .run/engine_dir.env; \
        echo "[pipeline] Using engine from .run/engine_dir.env: ${TRTLLM_ENGINE_DIR}"; \
    fi && \
    # Default engine dir based on precision mode
    if [ "${ORPHEUS_PRECISION_MODE:-quantized}" = "base" ]; then \
        export TRTLLM_ENGINE_DIR="${TRTLLM_ENGINE_DIR:-$PWD/models/orpheus-trt-8bit}"; \
    else \
        export TRTLLM_ENGINE_DIR="${TRTLLM_ENGINE_DIR:-$PWD/models/orpheus-trt-awq}"; \
    fi && \
    bash scripts/steps/03-run-server.sh
'

# Run pipeline in background with proper process isolation
echo "[pipeline] Starting complete setup pipeline in background..."
setsid nohup bash -lc "$PIPELINE_CMD" </dev/null >logs/setup-pipeline.log 2>&1 &

# Store background process ID
bg_pid=$!
echo $bg_pid >.run/setup-pipeline.pid

echo "[pipeline] Pipeline started (PID: $bg_pid)"
echo "[pipeline] Logs: logs/setup-pipeline.log"
echo "[pipeline] Server logs: logs/server.log (when server starts)"
echo "[pipeline] To stop: bash scripts/stop.sh"
echo ""
echo "[pipeline] Following setup logs (Ctrl-C detaches, pipeline continues)..."

# Tail logs with graceful handling
touch logs/setup-pipeline.log || true
exec tail -n +1 -F logs/setup-pipeline.log
