#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Quantization Entry Point
# =============================================================================
# Entry point for TRT-LLM quantization pipeline.
# Handles pre-quantized model detection, on-the-fly quantization, and engine build.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Source common utilities
source "${SCRIPT_DIR}/../lib/common/log.sh"
source "${SCRIPT_DIR}/../lib/common/gpu_detect.sh"
source "${SCRIPT_DIR}/../lib/common/model_detect.sh"

# Source TRT libraries (must come after model_detect.sh for MoE detection)
source "${SCRIPT_DIR}/../lib/env/trt.sh"
source "${SCRIPT_DIR}/../engines/trt/install.sh"
source "${SCRIPT_DIR}/../engines/trt/detect.sh"
source "${SCRIPT_DIR}/../engines/trt/quantize.sh"
source "${SCRIPT_DIR}/../engines/trt/build.sh"
source "${SCRIPT_DIR}/../engines/trt/push.sh"

# =============================================================================
# MAIN LOGIC
# =============================================================================

# Check if we should run TRT quantization
TRT_TARGET_CHAT=0
if [ "${DEPLOY_CHAT:-0}" = "1" ] && [ "${INFERENCE_ENGINE:-vllm}" = "trt" ]; then
  TRT_TARGET_CHAT=1
fi

export TRT_TARGET_CHAT

# If TRT is not the target engine, exit quietly
if [ "${TRT_TARGET_CHAT}" = "0" ]; then
  # Return 0 when sourced, exit 0 when executed
  return 0 2>/dev/null || exit 0
fi

log_info "[quant] Starting TRT-LLM quantization..."

# Initialize GPU detection
gpu_init_detection "trt-quant"

# Ensure TRT-LLM repository is available (contains quantization scripts)
if ! trt_prepare_repo; then
  log_err "[quant] ✗ Failed to prepare TensorRT-LLM repository"
  exit 1
fi

# =============================================================================
# EARLY VALIDATION: TRT_MAX_BATCH_SIZE required for engine build
# =============================================================================
# TRT_MAX_BATCH_SIZE is baked into the compiled engine and MUST be set.
# This is NOT the same as MAX_CONCURRENT_CONNECTIONS (WebSocket connections).
# Fail early before any heavy operations (downloads, quantization).
if ! trt_validate_batch_size; then
  exit 1
fi

# Export TRT environment
trt_export_env

# Determine the model to quantize
MODEL_ID="${CHAT_MODEL:-}"
if [ -z "${MODEL_ID}" ]; then
  log_err "[quant] ✗ CHAT_MODEL is not set"
  exit 1
fi

# Resolve quantization format (pass model ID for MoE detection)
QFORMAT=$(trt_resolve_qformat "${QUANTIZATION:-4bit}" "${GPU_SM_ARCH:-}" "${MODEL_ID}")
log_info "[quant] Quantization format: ${QFORMAT}"

# Check if model is already TRT pre-quantized
if trt_is_prequantized_model "${MODEL_ID}"; then
  log_info "[quant] Detected pre-quantized TRT model: ${MODEL_ID}"
  
  # Download pre-quantized checkpoint
  CHECKPOINT_DIR=$(trt_download_prequantized "${MODEL_ID}")
  if [ -z "${CHECKPOINT_DIR}" ]; then
    log_err "[quant] ✗ Failed to download pre-quantized model"
    exit 1
  fi
  
  TRT_CHECKPOINT_DIR="${CHECKPOINT_DIR}"
  export TRT_CHECKPOINT_DIR
  
  log_info "[quant] Using pre-quantized checkpoint: ${TRT_CHECKPOINT_DIR}"
else
  # Get checkpoint directory
  CHECKPOINT_DIR=$(trt_get_checkpoint_dir "${MODEL_ID}" "${QFORMAT}")
  
  # Check if checkpoint already exists
  if [ -d "${CHECKPOINT_DIR}" ] && [ -f "${CHECKPOINT_DIR}/config.json" ]; then
    if [ "${FORCE_REBUILD:-false}" != "true" ]; then
      log_info "[quant] Reusing existing checkpoint: ${CHECKPOINT_DIR}"
      TRT_CHECKPOINT_DIR="${CHECKPOINT_DIR}"
      export TRT_CHECKPOINT_DIR
    else
      log_info "[quant] FORCE_REBUILD=true, will re-quantize"
    fi
  fi
  
  # Quantize if needed
  if [ -z "${TRT_CHECKPOINT_DIR:-}" ]; then
    if ! trt_quantize_model "${MODEL_ID}" "${CHECKPOINT_DIR}" "${QFORMAT}"; then
      log_err "[quant] ✗ Quantization failed"
      exit 1
    fi
    TRT_CHECKPOINT_DIR="${CHECKPOINT_DIR}"
    export TRT_CHECKPOINT_DIR
  fi
fi

# Validate checkpoint
if ! trt_validate_checkpoint "${TRT_CHECKPOINT_DIR}"; then
  log_err "[quant] ✗ Checkpoint validation failed"
  exit 1
fi

# Get engine directory
ENGINE_DIR=$(trt_get_engine_dir "${MODEL_ID}" "${QFORMAT}")

# Check if engine already exists
if [ -d "${ENGINE_DIR}" ] && ls "${ENGINE_DIR}"/rank*.engine >/dev/null 2>&1; then
  if [ "${FORCE_REBUILD:-false}" != "true" ]; then
    log_info "[build] Reusing existing engine: ${ENGINE_DIR}"
    TRT_ENGINE_DIR="${ENGINE_DIR}"
    export TRT_ENGINE_DIR TRTLLM_ENGINE_DIR="${ENGINE_DIR}"
  else
    log_info "[build] FORCE_REBUILD=true, will rebuild engine"
  fi
fi

# Build engine if needed
if [ -z "${TRT_ENGINE_DIR:-}" ]; then
  log_info "[build] Building TRT engine..."
  if ! trt_build_engine "${TRT_CHECKPOINT_DIR}" "${ENGINE_DIR}"; then
    log_err "[build] ✗ Engine build failed"
    exit 1
  fi
  TRT_ENGINE_DIR="${ENGINE_DIR}"
  export TRT_ENGINE_DIR TRTLLM_ENGINE_DIR="${ENGINE_DIR}"
fi

# Validate engine
if ! trt_validate_engine "${TRT_ENGINE_DIR}"; then
  log_err "[build] ✗ Engine validation failed"
  exit 1
fi

# Save engine dir for server startup
mkdir -p "${ROOT_DIR}/.run"
echo "export TRTLLM_ENGINE_DIR='${TRT_ENGINE_DIR}'" > "${ROOT_DIR}/.run/trt_engine_dir.env"

# Optional: Push to HuggingFace (only when --push-quant flag is passed)
if [ "${HF_AWQ_PUSH:-0}" = "1" ]; then
  trt_push_to_hf "${TRT_CHECKPOINT_DIR}" "${TRT_ENGINE_DIR}"
fi

log_info "[quant] ✓ Complete: ${TRT_ENGINE_DIR}"

