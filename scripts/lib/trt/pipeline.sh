#!/usr/bin/env bash
# =============================================================================
# TRT Quantize/Build Shared Pipeline
# =============================================================================
# Shared orchestration for TRT checkpoint preparation, engine build, and pushes.

_TRT_PIPELINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -z "${ROOT_DIR:-}" ]; then
  ROOT_DIR="$(cd "${_TRT_PIPELINE_DIR}/../../.." && pwd)"
fi
source "${_TRT_PIPELINE_DIR}/../../config/values/core.sh"
source "${_TRT_PIPELINE_DIR}/../../config/values/runtime.sh"
source "${_TRT_PIPELINE_DIR}/../../config/patterns.sh"

trt_export_quant_env() {
  local qformat="${1:-}"
  if [ -z "${qformat}" ]; then
    return 0
  fi
  TRT_QFORMAT="${qformat}"
  TRT_QUANT_METHOD="${qformat}"
  export TRT_QFORMAT TRT_QUANT_METHOD
  return 0
}

trt_pipeline_should_run() {
  if [ "${DEPLOY_CHAT:-0}" = "1" ] && [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" = "${CFG_ENGINE_TRT}" ]; then
    return 0
  fi
  return 1
}

trt_pipeline_init() {
  log_blank
  gpu_init_detection "trt-quant"

  if ! trt_prepare_repo; then
    log_err "[quant] ✗ Failed to prepare TensorRT-LLM repository"
    return 1
  fi

  if ! validate_batch_size; then
    return 1
  fi

  export_env
  return 0
}

trt_pipeline_resolve_model() {
  MODEL_ID="${CHAT_MODEL:-}"
  if [ -z "${MODEL_ID}" ]; then
    log_err "[quant] ✗ CHAT_MODEL is not set"
    return 1
  fi

  QFORMAT="$(resolve_qformat "${CHAT_QUANTIZATION:-4bit}" "${GPU_SM_ARCH:-}" "${MODEL_ID}")"
  trt_export_quant_env "${QFORMAT}"

  export MODEL_ID QFORMAT
  return 0
}

trt_pipeline_prepare_checkpoint() {
  DID_QUANTIZE=0
  PREBUILT_ENGINE_LABEL=""
  PREBUILT_ENGINE_DIR=""
  USING_PREBUILT_ENGINE=0
  export DID_QUANTIZE USING_PREBUILT_ENGINE

  if is_trt_prequant "${MODEL_ID}"; then
    local trt_prequant_kind
    trt_prequant_kind="$(classify_trt "${MODEL_ID}")"
    if [ -n "${trt_prequant_kind}" ]; then
      log_info "[quant] Detected that we'll use a pre-quantized TRT model (${trt_prequant_kind})"
    else
      log_info "[quant] Detected that we'll use a pre-quantized TRT model: ${MODEL_ID}"
    fi

    local guessed_qformat
    guessed_qformat="$(detect_qformat_from_name "${MODEL_ID}" 2>/dev/null || true)"
    if [ -n "${guessed_qformat}" ]; then
      QFORMAT="${guessed_qformat}"
      trt_export_quant_env "${QFORMAT}"
    fi

    PREBUILT_ENGINE_LABEL="$(find_compatible_engine "${MODEL_ID}")" || true
    if [ -n "${PREBUILT_ENGINE_LABEL}" ]; then
      log_info "[quant] Using pre-built engine: ${PREBUILT_ENGINE_LABEL}"
      PREBUILT_ENGINE_DIR="$(download_prebuilt_engine "${MODEL_ID}" "${PREBUILT_ENGINE_LABEL}")" || {
        log_warn "[quant] ⚠ Failed to download pre-built engine, will build from checkpoint"
        PREBUILT_ENGINE_LABEL=""
      }
    fi

    TRT_CHECKPOINT_DIR="$(download_prequantized "${MODEL_ID}")"
    if [ -z "${TRT_CHECKPOINT_DIR}" ]; then
      log_err "[quant] ✗ Failed to download pre-quantized model"
      return 1
    fi
    export TRT_CHECKPOINT_DIR

    local detected_qformat
    detected_qformat="$(detect_qformat_from_checkpoint "${TRT_CHECKPOINT_DIR}" || true)"
    if [ -n "${detected_qformat}" ]; then
      QFORMAT="${detected_qformat}"
      trt_export_quant_env "${QFORMAT}"
    fi

    if [ -n "${PREBUILT_ENGINE_LABEL}" ] && [ -n "${PREBUILT_ENGINE_DIR}" ]; then
      TRT_ENGINE_DIR="${PREBUILT_ENGINE_DIR}"
      USING_PREBUILT_ENGINE=1
      export TRT_ENGINE_DIR USING_PREBUILT_ENGINE
    fi
  else
    local checkpoint_dir
    checkpoint_dir="$(get_checkpoint_dir "${MODEL_ID}" "${QFORMAT}")"

    if [ -d "${checkpoint_dir}" ] && [ -f "${checkpoint_dir}/config.json" ]; then
      if [ "${FORCE_REBUILD:-false}" != "true" ]; then
        log_info "[quant] Reusing existing checkpoint"
        TRT_CHECKPOINT_DIR="${checkpoint_dir}"
        export TRT_CHECKPOINT_DIR
      else
        log_info "[quant] FORCE_REBUILD=true, will re-quantize"
      fi
    fi

    if [ -z "${TRT_CHECKPOINT_DIR:-}" ]; then
      if ! quantize_model "${MODEL_ID}" "${checkpoint_dir}" "${QFORMAT}"; then
        log_err "[quant] ✗ Quantization failed"
        return 1
      fi
      TRT_CHECKPOINT_DIR="${checkpoint_dir}"
      DID_QUANTIZE=1
      export TRT_CHECKPOINT_DIR DID_QUANTIZE
    fi
  fi

  return 0
}

trt_pipeline_prepare_engine() {
  if ! validate_checkpoint "${TRT_CHECKPOINT_DIR}"; then
    log_err "[quant] ✗ Checkpoint validation failed"
    return 1
  fi

  if [ "${DID_QUANTIZE:-0}" = "1" ]; then
    log_info "[quant] ✓ Quantization process complete"
  fi
  log_blank

  if [ "${USING_PREBUILT_ENGINE:-0}" = "1" ]; then
    log_info "[build] Using pre-built engine from HuggingFace..."
  else
    local engine_dir
    engine_dir="$(get_engine_dir "${MODEL_ID}" "${QFORMAT}")"

    if [ -d "${engine_dir}" ] && ls "${engine_dir}"/rank*.engine >/dev/null 2>&1; then
      if [ "${FORCE_REBUILD:-false}" != "true" ]; then
        log_info "[build] Reusing existing local engine..."
        TRT_ENGINE_DIR="${engine_dir}"
        export TRT_ENGINE_DIR
      else
        log_info "[build] FORCE_REBUILD=true, will rebuild engine"
      fi
    fi

    if [ -z "${TRT_ENGINE_DIR:-}" ]; then
      if ! build_engine "${TRT_CHECKPOINT_DIR}" "${engine_dir}"; then
        log_err "[build] ✗ Engine build failed"
        return 1
      fi
      TRT_ENGINE_DIR="${engine_dir}"
      export TRT_ENGINE_DIR
    fi
  fi

  if ! validate_engine "${TRT_ENGINE_DIR}"; then
    log_err "[build] ✗ Engine validation failed"
    return 1
  fi

  mkdir -p "${ROOT_DIR}/${CFG_RUNTIME_RUN_DIR}"
  echo "export TRT_ENGINE_DIR='${TRT_ENGINE_DIR}'" >"${ROOT_DIR}/${CFG_RUNTIME_TRT_ENGINE_ENV_FILE}"
  return 0
}

trt_pipeline_push_artifacts() {
  if [ "${HF_AWQ_PUSH:-0}" = "1" ]; then
    if ! push_to_hf "${TRT_CHECKPOINT_DIR}" "${TRT_ENGINE_DIR}"; then
      return 1
    fi
  fi

  if [ "${HF_ENGINE_PUSH:-0}" = "1" ] && [ "${HF_AWQ_PUSH:-0}" != "1" ]; then
    if [ "${USING_PREBUILT_ENGINE:-0}" = "1" ]; then
      log_info "[quant] --push-engine skipped: engine was downloaded from HuggingFace"
    elif is_trt_prequant "${MODEL_ID}"; then
      if ! push_engine_to_hf "${TRT_ENGINE_DIR}" "${MODEL_ID}"; then
        return 1
      fi
    else
      log_info "[quant] --push-engine specified but model is not prequantized; skipping"
      log_info "[quant]   Use --push-quant to push local quantization artifacts instead"
    fi
  fi

  return 0
}

trt_pipeline_run() {
  trt_pipeline_init || return 1
  trt_pipeline_resolve_model || return 1
  trt_pipeline_prepare_checkpoint || return 1
  trt_pipeline_prepare_engine || return 1
  trt_pipeline_push_artifacts || return 1
  return 0
}
