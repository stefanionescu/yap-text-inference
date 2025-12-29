#!/usr/bin/env bash

# Helper utilities for inferring quantization hints from model identifiers.

_model_detect_lower() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    echo ""
    return
  fi
  if [[ -n "${BASH_VERSION:-}" && "${BASH_VERSION%%.*}" -ge 4 ]]; then
    echo "${value,,}"
  else
    echo "${value}" | tr '[:upper:]' '[:lower:]'
  fi
}

_model_detect_has_marker() {
  local lowered="$1"
  local marker="$2"
  [[ "${lowered}" == *"${marker}"* ]]
}

_model_detect_has_any_marker() {
  local lowered="$1"
  shift
  local marker
  for marker in "$@"; do
    if _model_detect_has_marker "${lowered}" "${marker}"; then
      return 0
    fi
  done
  return 1
}

model_detect_is_gptq_name() {
  local value="${1:-}"
  local lowered
  lowered="$(_model_detect_lower "${value}")"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  _model_detect_has_marker "${lowered}" "gptq"
}

model_detect_has_w4a16_hint() {
  local value="${1:-}"
  local lowered
  lowered="$(_model_detect_lower "${value}")"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  _model_detect_has_any_marker "${lowered}" \
    "w4a16" \
    "compressed-tensors" \
    "autoround"
}

model_detect_is_awq_name() {
  local value="${1:-}"
  local lowered
  lowered="$(_model_detect_lower "${value}")"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  if _model_detect_has_marker "${lowered}" "awq"; then
    return 0
  fi
  model_detect_has_w4a16_hint "${lowered}"
}

model_detect_classify_prequant() {
  local value="${1:-}"
  if model_detect_is_awq_name "${value}"; then
    echo "awq"
    return
  fi
  if model_detect_is_gptq_name "${value}"; then
    echo "gptq"
    return
  fi
  echo ""
}

model_detect_quantization_hint() {
  local classification
  classification="$(model_detect_classify_prequant "$1")"
  case "${classification}" in
    awq) echo "awq" ;;
    gptq) echo "gptq_marlin" ;;
    *) echo "" ;;
  esac
}

model_detect_is_prequant_awq() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    return 1
  fi
  if model_detect_is_awq_name "${value}"; then
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
_model_detect_trt_prequant_kind() {
  local lowered="$1"
  if [ -z "${lowered}" ]; then
    return 1
  fi
  if ! _model_detect_has_marker "${lowered}" "trt"; then
    return 1
  fi
  if _model_detect_has_marker "${lowered}" "awq"; then
    echo "trt_awq"
    return 0
  fi
  if _model_detect_has_marker "${lowered}" "fp8"; then
    echo "trt_fp8"
    return 0
  fi
  if _model_detect_has_any_marker "${lowered}" "int8" "int-8"; then
    echo "trt_int8"
    return 0
  fi
  if _model_detect_has_any_marker "${lowered}" "8bit" "8-bit"; then
    echo "trt_8bit"
    return 0
  fi
  return 1
}

model_detect_is_trt_prequant() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    return 1
  fi
  local lowered
  lowered="$(_model_detect_lower "${value}")"
  if _model_detect_trt_prequant_kind "${lowered}" >/dev/null; then
    return 0
  fi
  return 1
}

# Check if model is a MoE (Mixture of Experts) model
model_detect_is_moe() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    return 1
  fi
  local lowered
  lowered="$(_model_detect_lower "${value}")"
  
  # Check for Qwen3 MoE naming: -aXb suffix
  if echo "${lowered}" | grep -qE -- '-a[0-9]+b'; then
    return 0
  fi
  
  # Check common MoE markers
  if _model_detect_has_any_marker "${lowered}" "moe" "mixtral" "deepseek-v2" "deepseek-v3" "ernie-4.5"; then
    return 0
  fi
  
  return 1
}

# Classify model for TRT (returns: trt_awq, trt_fp8, trt_int8, trt_8bit, moe, or empty)
model_detect_classify_trt() {
  local value="${1:-}"
  local lowered
  lowered="$(_model_detect_lower "${value}")"
  local kind=""
  if kind="$(_model_detect_trt_prequant_kind "${lowered}")"; then
    echo "${kind}"
    return
  fi
  if model_detect_is_moe "${value}"; then
    echo "moe"
    return
  fi
  echo ""
}

# =============================================================================
# PREQUANTIZED MODEL + PUSH VALIDATION
# =============================================================================

# Check if any of the provided models are prequantized
model_detect_any_prequant() {
  local chat_model="${1:-}"
  local tool_model="${2:-}"
  
  if [ -n "${chat_model}" ]; then
    if model_detect_is_awq_name "${chat_model}" || model_detect_is_gptq_name "${chat_model}" || model_detect_is_trt_prequant "${chat_model}"; then
      echo "${chat_model}"
      return 0
    fi
  fi
  if [ -n "${tool_model}" ]; then
    if model_detect_is_awq_name "${tool_model}" || model_detect_is_gptq_name "${tool_model}" || model_detect_is_trt_prequant "${tool_model}"; then
      echo "${tool_model}"
      return 0
    fi
  fi
  echo ""
  return 1
}

# Validate that --push-quant is not used with a prequantized model
# Returns 0 if valid, 1 if invalid (with error messages)
model_detect_validate_push_quant_prequant() {
  local chat_model="${1:-}"
  local tool_model="${2:-}"
  local push_requested="${3:-${HF_AWQ_PUSH_REQUESTED:-0}}"
  local prefix="${4:-[main]}"
  
  if [ "${push_requested}" != "1" ]; then
    return 0
  fi
  
  local prequant_model
  prequant_model="$(model_detect_any_prequant "${chat_model}" "${tool_model}")"
  
  if [ -n "${prequant_model}" ]; then
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
