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
source "${SCRIPT_DIR}/../lib/common/hf.sh"

# Source TRT libraries (must come after model_detect.sh for MoE detection)
source "${SCRIPT_DIR}/../lib/env/trt.sh"
source "${SCRIPT_DIR}/../engines/trt/install.sh"
source "${SCRIPT_DIR}/../engines/trt/detect.sh"
source "${SCRIPT_DIR}/../engines/trt/quantize.sh"
source "${SCRIPT_DIR}/../engines/trt/build.sh"
source "${SCRIPT_DIR}/../engines/trt/push.sh"

# =============================================================================
# HELPERS
# =============================================================================

_trt_export_quant_env() {
  local qformat="$1"
  if [ -z "${qformat}" ]; then
    return
  fi
  TRT_QFORMAT="${qformat}"
  TRT_QUANT_METHOD="${qformat}"
  export TRT_QFORMAT TRT_QUANT_METHOD
}

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
  # shellcheck disable=SC2317  # Intentional: return when sourced, exit when executed
  return 0 2>/dev/null || exit 0
fi

log_blank

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
if ! validate_batch_size; then
  exit 1
fi

# Export TRT environment
export_env

# Determine the model to quantize
MODEL_ID="${CHAT_MODEL:-}"
if [ -z "${MODEL_ID}" ]; then
  log_err "[quant] ✗ CHAT_MODEL is not set"
  exit 1
fi

# Track if we perform quantization (vs reusing cached/downloaded checkpoints)
DID_QUANTIZE=0

# Resolve quantization format (pass model ID for MoE detection)
QFORMAT=$(resolve_qformat "${CHAT_QUANTIZATION:-4bit}" "${GPU_SM_ARCH:-}" "${MODEL_ID}")
_trt_export_quant_env "${QFORMAT}"

# Check if model is already TRT pre-quantized
if is_trt_prequant "${MODEL_ID}"; then
  trt_prequant_kind="$(classify_trt "${MODEL_ID}")"
  if [ -n "${trt_prequant_kind}" ]; then
    log_info "[quant] Detected that we'll use a pre-quantized TRT model (${trt_prequant_kind})"
  else
    log_info "[quant] Detected that we'll use a pre-quantized TRT model: ${MODEL_ID}"
  fi

  guessed_qformat="$(detect_qformat_from_name "${MODEL_ID}" 2>/dev/null || true)"
  if [ -n "${guessed_qformat}" ]; then
    QFORMAT="${guessed_qformat}"
    _trt_export_quant_env "${QFORMAT}"
  fi
  
  # Check for pre-built engine in the HF repo FIRST
  PREBUILT_ENGINE_LABEL=""
  PREBUILT_ENGINE_LABEL=$(find_compatible_engine "${MODEL_ID}") || true
  
  if [ -n "${PREBUILT_ENGINE_LABEL}" ]; then
    # Download the pre-built engine - skip engine building later
    log_info "[quant] Using pre-built engine: ${PREBUILT_ENGINE_LABEL}"
    PREBUILT_ENGINE_DIR=$(download_prebuilt_engine "${MODEL_ID}" "${PREBUILT_ENGINE_LABEL}") || {
      log_warn "[quant] ⚠ Failed to download pre-built engine, will build from checkpoint"
      PREBUILT_ENGINE_LABEL=""
    }
  fi
  
  # Download pre-quantized checkpoint (needed for tokenizer and config even if using pre-built engine)
  CHECKPOINT_DIR=$(download_prequantized "${MODEL_ID}")
  if [ -z "${CHECKPOINT_DIR}" ]; then
    log_err "[quant] ✗ Failed to download pre-quantized model"
    exit 1
  fi
  
  TRT_CHECKPOINT_DIR="${CHECKPOINT_DIR}"
  export TRT_CHECKPOINT_DIR

  detected_qformat="$(detect_qformat_from_checkpoint "${TRT_CHECKPOINT_DIR}" || true)"
  if [ -n "${detected_qformat}" ]; then
    QFORMAT="${detected_qformat}"
    _trt_export_quant_env "${QFORMAT}"
  fi
  
  # If we have a pre-built engine, use it and skip the engine build section later
  if [ -n "${PREBUILT_ENGINE_LABEL}" ] && [ -n "${PREBUILT_ENGINE_DIR:-}" ]; then
    TRT_ENGINE_DIR="${PREBUILT_ENGINE_DIR}"
    export TRT_ENGINE_DIR
    USING_PREBUILT_ENGINE=1
    export USING_PREBUILT_ENGINE
  fi
else
  # Get checkpoint directory
  CHECKPOINT_DIR=$(get_checkpoint_dir "${MODEL_ID}" "${QFORMAT}")
  
  # Check if checkpoint already exists
  if [ -d "${CHECKPOINT_DIR}" ] && [ -f "${CHECKPOINT_DIR}/config.json" ]; then
    if [ "${FORCE_REBUILD:-false}" != "true" ]; then
      log_info "[quant] Reusing existing checkpoint"
      TRT_CHECKPOINT_DIR="${CHECKPOINT_DIR}"
      export TRT_CHECKPOINT_DIR
    else
      log_info "[quant] FORCE_REBUILD=true, will re-quantize"
    fi
  fi
  
  # Quantize if needed
  if [ -z "${TRT_CHECKPOINT_DIR:-}" ]; then
    if ! quantize_model "${MODEL_ID}" "${CHECKPOINT_DIR}" "${QFORMAT}"; then
      log_err "[quant] ✗ Quantization failed"
      exit 1
    fi
    TRT_CHECKPOINT_DIR="${CHECKPOINT_DIR}"
    export TRT_CHECKPOINT_DIR
    DID_QUANTIZE=1
  fi
fi

# Validate checkpoint
if ! validate_checkpoint "${TRT_CHECKPOINT_DIR}"; then
  log_err "[quant] ✗ Checkpoint validation failed"
  exit 1
fi

# Only print if we ran quantization (not reused cached/remote checkpoint)
if [ "${DID_QUANTIZE}" = "1" ]; then
  log_info "[quant] ✓ Quantization process complete"
fi
log_blank

# Skip engine build if we're using a pre-built engine from HuggingFace
if [ "${USING_PREBUILT_ENGINE:-0}" = "1" ]; then
  log_info "[build] Using pre-built engine from HuggingFace..."
else
  # Get engine directory
  ENGINE_DIR=$(get_engine_dir "${MODEL_ID}" "${QFORMAT}")

  # Check if engine already exists locally
  if [ -d "${ENGINE_DIR}" ] && ls "${ENGINE_DIR}"/rank*.engine >/dev/null 2>&1; then
    if [ "${FORCE_REBUILD:-false}" != "true" ]; then
      log_info "[build] Reusing existing local engine..."
      TRT_ENGINE_DIR="${ENGINE_DIR}"
      export TRT_ENGINE_DIR
    else
      log_info "[build] FORCE_REBUILD=true, will rebuild engine"
    fi
  fi

  # Build engine if needed
  if [ -z "${TRT_ENGINE_DIR:-}" ]; then
    if ! build_engine "${TRT_CHECKPOINT_DIR}" "${ENGINE_DIR}"; then
      log_err "[build] ✗ Engine build failed"
      exit 1
    fi
    TRT_ENGINE_DIR="${ENGINE_DIR}"
    export TRT_ENGINE_DIR
  fi
fi

# Validate engine
if ! validate_engine "${TRT_ENGINE_DIR}"; then
  log_err "[build] ✗ Engine validation failed"
  exit 1
fi

# Save engine dir for server startup
mkdir -p "${ROOT_DIR}/.run"
echo "export TRT_ENGINE_DIR='${TRT_ENGINE_DIR}'" > "${ROOT_DIR}/.run/trt_engine_dir.env"

# Optional: Push to HuggingFace (only when --push-quant flag is passed)
if [ "${HF_AWQ_PUSH:-0}" = "1" ]; then
  push_to_hf "${TRT_CHECKPOINT_DIR}" "${TRT_ENGINE_DIR}"
fi

# Optional: Push engine only to existing HuggingFace repo (for prequantized models)
# Only runs when:
# 1. --push-engine flag is passed (HF_ENGINE_PUSH=1)
# 2. Using a prequantized model (skip if we already did a full push above)
# 3. NOT using a pre-built engine from HuggingFace (no point pushing back what we downloaded)
if [ "${HF_ENGINE_PUSH:-0}" = "1" ] && [ "${HF_AWQ_PUSH:-0}" != "1" ]; then
  if [ "${USING_PREBUILT_ENGINE:-0}" = "1" ]; then
    log_info "[quant] --push-engine skipped: engine was downloaded from HuggingFace"
  elif is_trt_prequant "${MODEL_ID}"; then
    push_engine_to_hf "${TRT_ENGINE_DIR}" "${MODEL_ID}"
  else
    log_info "[quant] --push-engine specified but model is not prequantized; skipping"
    log_info "[quant]   Use --push-quant to push local quantization artifacts instead"
  fi
fi
