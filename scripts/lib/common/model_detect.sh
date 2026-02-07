#!/usr/bin/env bash
# =============================================================================
# Model Detection Utilities
# =============================================================================
# Helper utilities for inferring quantization hints from model identifiers.
# Detects pre-quantized models (AWQ, GPTQ, TRT) and MoE architectures.

_MODEL_DETECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=string.sh
source "${_MODEL_DETECT_DIR}/string.sh"

is_gptq_name() {
  local value="${1:-}"
  local lowered
  lowered="$(str_to_lower "${value}")"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  str_contains "${lowered}" "gptq"
}

has_w4a16_hint() {
  local value="${1:-}"
  local lowered
  lowered="$(str_to_lower "${value}")"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  str_contains_any "${lowered}" \
    "w4a16" \
    "compressed-tensors" \
    "autoround"
}

is_awq_name() {
  local value="${1:-}"
  local lowered
  lowered="$(str_to_lower "${value}")"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  if str_contains "${lowered}" "awq"; then
    return 0
  fi
  has_w4a16_hint "${lowered}"
}

classify_prequant() {
  local value="${1:-}"
  if is_awq_name "${value}"; then
    echo "awq"
    return
  fi
  if is_gptq_name "${value}"; then
    echo "gptq"
    return
  fi
  echo ""
}

get_quantization_hint() {
  local classification
  classification="$(classify_prequant "$1")"
  case "${classification}" in
    awq) echo "awq" ;;
    gptq) echo "gptq_marlin" ;;
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
  if ! str_contains "${lowered}" "trt"; then
    return 1
  fi
  if str_contains "${lowered}" "awq"; then
    echo "trt_awq"
    return 0
  fi
  if str_contains "${lowered}" "fp8"; then
    echo "trt_fp8"
    return 0
  fi
  if str_contains_any "${lowered}" "int8" "int-8"; then
    echo "trt_int8"
    return 0
  fi
  if str_contains_any "${lowered}" "8bit" "8-bit"; then
    echo "trt_8bit"
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
  if echo "${lowered}" | grep -qE -- '-a[0-9]+b'; then
    return 0
  fi

  # Check common MoE markers
  if str_contains_any "${lowered}" "moe" "mixtral" "deepseek-v2" "deepseek-v3" "ernie-4.5"; then
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
    echo "moe"
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
