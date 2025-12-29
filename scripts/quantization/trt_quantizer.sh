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

_trt_guess_qformat_from_name() {
  local name="$1"
  if [ -z "${name}" ]; then
    return 1
  fi
  local lowered
  lowered="${name,,}"
  if [[ "${lowered}" == *awq* ]]; then
    echo "int4_awq"
    return 0
  fi
  if [[ "${lowered}" == *fp8* ]]; then
    echo "fp8"
    return 0
  fi
  if [[ "${lowered}" == *int8* ]] || [[ "${lowered}" == *int-8* ]]; then
    echo "int8_sq"
    return 0
  fi
  if [[ "${lowered}" == *8bit* ]] || [[ "${lowered}" == *8-bit* ]]; then
    echo "fp8"
    return 0
  fi
  return 1
}

_trt_detect_qformat_from_checkpoint() {
  local ckpt_dir="$1"
  if [ -z "${ckpt_dir}" ] || [ ! -f "${ckpt_dir}/config.json" ]; then
    return 1
  fi
  local detected
  detected="$(
    python - "${ckpt_dir}" 2>/dev/null <<'PY' || true
import json
import sys
from pathlib import Path

cfg_path = Path(sys.argv[1]) / "config.json"
try:
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
except Exception:
    sys.exit(0)

quant = {}
for key in ("quantization_config", "quantization", "quant_config"):
    value = data.get(key)
    if isinstance(value, dict) and value:
        quant = value
        break

algo = ""
if isinstance(quant, dict):
    raw_algo = quant.get("quant_algo") or quant.get("algorithm") or quant.get("quantization_algo") or quant.get("quantization_method")
    if isinstance(raw_algo, str):
        algo = raw_algo.lower()
    w_bit = quant.get("w_bit") or quant.get("weight_bits") or quant.get("weight_bit") or quant.get("quant_bits")
    try:
        if isinstance(w_bit, str):
            w_bit = int(w_bit)
    except Exception:
        w_bit = None
else:
    w_bit = None

def emit(value):
    if value:
        print(value)
        sys.exit(0)

if "fp8" in algo:
    emit("fp8")
if "int8" in algo or "sq" in algo:
    emit("int8_sq")
if "int4" in algo or "awq" in algo:
    emit("int4_awq")
if isinstance(w_bit, int):
    if w_bit <= 4:
        emit("int4_awq")
    if w_bit >= 8:
        emit("fp8")

sys.exit(0)
PY
  )"
  detected="${detected%%$'\n'}"
  if [ -n "${detected}" ]; then
    echo "${detected}"
    return 0
  fi
  return 1
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
  return 0 2>/dev/null || exit 0
fi

log_section "[quant] Starting TRT-LLM quantization..."

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
_trt_export_quant_env "${QFORMAT}"

# Check if model is already TRT pre-quantized
if model_detect_is_trt_prequant "${MODEL_ID}"; then
  trt_prequant_kind="$(model_detect_classify_trt "${MODEL_ID}")"
  if [ -n "${trt_prequant_kind}" ]; then
    log_info "[quant] Detected pre-quantized TRT model (${trt_prequant_kind})"
  else
    log_info "[quant] Detected pre-quantized TRT model: ${MODEL_ID}"
  fi

  guessed_qformat="$(_trt_guess_qformat_from_name "${MODEL_ID}" 2>/dev/null || true)"
  if [ -n "${guessed_qformat}" ]; then
    QFORMAT="${guessed_qformat}"
    _trt_export_quant_env "${QFORMAT}"
  fi
  
  # Download pre-quantized checkpoint
  CHECKPOINT_DIR=$(trt_download_prequantized "${MODEL_ID}")
  if [ -z "${CHECKPOINT_DIR}" ]; then
    log_err "[quant] ✗ Failed to download pre-quantized model"
    exit 1
  fi
  
  TRT_CHECKPOINT_DIR="${CHECKPOINT_DIR}"
  export TRT_CHECKPOINT_DIR
  
  log_info "[quant] Using pre-quantized checkpoint: ${TRT_CHECKPOINT_DIR}"

  detected_qformat="$(_trt_detect_qformat_from_checkpoint "${TRT_CHECKPOINT_DIR}" || true)"
  if [ -n "${detected_qformat}" ]; then
    QFORMAT="${detected_qformat}"
    _trt_export_quant_env "${QFORMAT}"
  fi
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

log_info "[quant] ✓ Quantization process complete"
log_blank
