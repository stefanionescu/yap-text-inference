#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Model Detection Utilities
# =============================================================================
# Helper utilities for inferring quantization hints from model identifiers.
# Detects pre-quantized models (AWQ, GPTQ, TRT) and MoE architectures.

_MODEL_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../string.sh
source "${_MODEL_LIB_DIR}/../string.sh"
# shellcheck source=../../../config/values/model.sh
source "${_MODEL_LIB_DIR}/../../../config/values/model.sh"
# shellcheck source=../../../config/patterns.sh
source "${_MODEL_LIB_DIR}/../../../config/patterns.sh"

is_gptq_name() {
  local value="${1:-}"
  local lowered
  lowered="$(str_to_lower "${value}")"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  str_contains "${lowered}" "${CFG_MODEL_TOKEN_GPTQ}"
}

has_w4a16_hint() {
  local value="${1:-}"
  local lowered
  lowered="$(str_to_lower "${value}")"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  str_contains_any "${lowered}" \
    "${CFG_MODEL_TOKEN_W4A16}" \
    "${CFG_MODEL_TOKEN_COMPRESSED_TENSORS}" \
    "${CFG_MODEL_TOKEN_AUTOROUND}"
}

is_awq_name() {
  local value="${1:-}"
  local lowered
  lowered="$(str_to_lower "${value}")"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  if str_contains "${lowered}" "${CFG_MODEL_TOKEN_AWQ}"; then
    return 0
  fi
  has_w4a16_hint "${lowered}"
}

classify_prequant() {
  local value="${1:-}"
  if is_awq_name "${value}"; then
    echo "${CFG_MODEL_TOKEN_AWQ}"
    return
  fi
  if is_gptq_name "${value}"; then
    echo "${CFG_MODEL_TOKEN_GPTQ}"
    return
  fi
  echo ""
}

get_quantization_hint() {
  local classification
  classification="$(classify_prequant "$1")"
  case "${classification}" in
    "${CFG_MODEL_TOKEN_AWQ}") echo "${CFG_MODEL_TOKEN_AWQ}" ;;
    "${CFG_MODEL_TOKEN_GPTQ}") echo "${CFG_MODEL_TOKEN_GPTQ_MARLIN}" ;;
    *) echo "" ;;
  esac
}

is_prequant_awq() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    return 1
  fi
  if is_awq_name "${value}"; then
    return 0
  fi
  if [ -d "${value}" ] && { [ -f "${value}/awq_metadata.json" ] || [ -f "${value}/awq_config.json" ]; }; then
    return 0
  fi
  return 1
}

# =============================================================================
# TRT-LLM DETECTION
# =============================================================================

# Check if model is a TRT pre-quantized model (AWQ or 8-bit)
# Returns: trt_awq, trt_fp8, trt_int8, trt_8bit, or fails
_trt_prequant_kind() {
  local lowered="$1"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  if ! str_contains "${lowered}" "${CFG_MODEL_TOKEN_TRT}"; then
    return 1
  fi
  if str_contains "${lowered}" "${CFG_MODEL_TOKEN_AWQ}"; then
    echo "${CFG_MODEL_TRT_KIND_AWQ}"
    return 0
  fi
  if str_contains "${lowered}" "${CFG_MODEL_TOKEN_FP8}"; then
    echo "${CFG_MODEL_TRT_KIND_FP8}"
    return 0
  fi
  if str_contains_any "${lowered}" "${CFG_MODEL_TOKEN_INT8}" "${CFG_MODEL_TOKEN_INT8_DASHED}"; then
    echo "${CFG_MODEL_TRT_KIND_INT8}"
    return 0
  fi
  if str_contains_any "${lowered}" "${CFG_MODEL_TOKEN_8BIT}" "${CFG_MODEL_TOKEN_8BIT_DASHED}"; then
    echo "${CFG_MODEL_TRT_KIND_8BIT}"
    return 0
  fi
  return 1
}

is_trt_prequant() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    return 1
  fi
  local lowered
  lowered="$(str_to_lower "${value}")"
  if _trt_prequant_kind "${lowered}" >/dev/null; then
    return 0
  fi
  return 1
}

# Check if model is a MoE (Mixture of Experts) model
is_moe() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    return 1
  fi
  local lowered
  lowered="$(str_to_lower "${value}")"

  # Check for Qwen3 MoE naming: -aXb suffix
  if echo "${lowered}" | grep -qE -- "${CFG_PATTERN_QWEN_MOE_SUFFIX}"; then
    return 0
  fi

  # Check common MoE markers
  if str_contains_any "${lowered}" \
    "${CFG_MODEL_TOKEN_MOE}" \
    "${CFG_MODEL_TOKEN_MIXTRAL}" \
    "${CFG_MODEL_TOKEN_DEEPSEEK_V2}" \
    "${CFG_MODEL_TOKEN_DEEPSEEK_V3}" \
    "${CFG_MODEL_TOKEN_ERNIE_45}"; then
    return 0
  fi

  return 1
}

# Classify model for TRT (returns: trt_awq, trt_fp8, trt_int8, trt_8bit, moe, or empty)
classify_trt() {
  local value="${1:-}"
  local lowered
  lowered="$(str_to_lower "${value}")"
  local kind=""
  if kind="$(_trt_prequant_kind "${lowered}")"; then
    echo "${kind}"
    return
  fi
  if is_moe "${value}"; then
    echo "${CFG_MODEL_TRT_KIND_MOE}"
    return
  fi
  echo ""
}

# =============================================================================
# PREQUANTIZED MODEL + PUSH VALIDATION
# =============================================================================

# Check if any of the provided models are prequantized
has_prequant_model() {
  local chat_model="${1:-}"
  local tool_model="${2:-}"

  if [ -n "${chat_model}" ]; then
    if is_awq_name "${chat_model}" || is_gptq_name "${chat_model}" || is_trt_prequant "${chat_model}"; then
      echo "${chat_model}"
      return 0
    fi
  fi
  if [ -n "${tool_model}" ]; then
    if is_awq_name "${tool_model}" || is_gptq_name "${tool_model}" || is_trt_prequant "${tool_model}"; then
      echo "${tool_model}"
      return 0
    fi
  fi
  echo ""
  return 1
}

# Check if local TRT checkpoint exists for a model
# Returns 0 if exists, 1 if not
_has_local_trt_checkpoint() {
  local model_id="${1:-}"
  local trt_cache="${TRT_CACHE_DIR:-${ROOT_DIR:-.}/.trt_cache}"

  if [ -z "${model_id}" ] || [ ! -d "${trt_cache}" ]; then
    return 1
  fi

  # Derive checkpoint name from model ID (same logic as get_checkpoint_dir)
  local model_name
  model_name=$(basename "${model_id}" | tr '[:upper:]' '[:lower:]' | tr '/' '-')

  # Check for any checkpoint directory matching this model
  for ckpt_dir in "${trt_cache}/${model_name}"-*-ckpt; do
    if [ -d "${ckpt_dir}" ] && [ -f "${ckpt_dir}/config.json" ]; then
      return 0
    fi
  done

  return 1
}

# Validate that --push-quant is not used with a prequantized model
# Exception: allow if local TRT checkpoint exists (locally quantized artifacts)
# Returns 0 if valid, 1 if invalid (with error messages)
validate_push_quant_prequant() {
  local chat_model="${1:-}"
  local tool_model="${2:-}"
  local push_requested="${3:-${HF_AWQ_PUSH_REQUESTED:-0}}"
  local prefix="${4:-[main]}"

  if [ "${push_requested}" != "1" ]; then
    return 0
  fi

  local prequant_model
  prequant_model="$(has_prequant_model "${chat_model}" "${tool_model}")"

  if [ -n "${prequant_model}" ]; then
    # Allow push if local TRT checkpoint exists (model was quantized locally)
    if _has_local_trt_checkpoint "${prequant_model}"; then
      return 0
    fi

    log_err "${prefix} ✗ Cannot use --push-quant with a prequantized model."
    log_err "${prefix}   Model '${prequant_model}' is already quantized."
    log_err "${prefix}   There are no local quantization artifacts to upload."
    log_blank
    log_err "${prefix}   Options:"
    log_err "${prefix}     1. Remove --push-quant to use the prequantized model directly"
    log_err "${prefix}     2. Use a base (non-quantized) model if you want to quantize and push"
    return 1
  fi

  return 0
}
