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
    "nvfp4" \
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

# Check if model is a TRT pre-quantized model (contains both 'trt' and 'awq')
model_detect_is_trt_prequant() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    return 1
  fi
  local lowered
  lowered="$(_model_detect_lower "${value}")"
  # Must contain both 'trt' and 'awq'
  if _model_detect_has_marker "${lowered}" "trt" && _model_detect_has_marker "${lowered}" "awq"; then
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

# Classify model for TRT (returns: trt_awq, moe, or empty)
model_detect_classify_trt() {
  local value="${1:-}"
  if model_detect_is_trt_prequant "${value}"; then
    echo "trt_awq"
    return
  fi
  if model_detect_is_moe "${value}"; then
    echo "moe"
    return
  fi
  echo ""
}

# Check if model name indicates NVFP4 quantization
model_detect_is_nvfp4() {
  local value="${1:-}"
  if [ -z "${value}" ]; then
    return 1
  fi
  local lowered
  lowered="$(_model_detect_lower "${value}")"
  _model_detect_has_marker "${lowered}" "nvfp4"
}

# Validate that NVFP4/MOE is not used on A100 (sm80)
# NVFP4 requires native FP4 support which A100 lacks
# Usage: model_detect_validate_nvfp4_gpu <model_id> <sm_arch> <is_moe_quantization>
# Returns 0 if valid, 1 if invalid (should block deployment)
model_detect_validate_nvfp4_gpu() {
  local model_id="${1:-}"
  local sm_arch="${2:-${GPU_SM_ARCH:-}}"
  local is_moe_quant="${3:-0}"
  
  # Only sm80 (A100) is blocked for NVFP4
  if [ "${sm_arch}" != "sm80" ]; then
    return 0
  fi
  
  # Check 1: Pre-quantized NVFP4 model on A100
  if model_detect_is_nvfp4 "${model_id}"; then
    return 1
  fi
  
  # Check 2: MoE model quantization on A100 (would use NVFP4)
  if [ "${is_moe_quant}" = "1" ]; then
    return 1
  fi
  
  # Check 3: MoE model on A100 with TRT (would need NVFP4)
  if model_detect_is_moe "${model_id}"; then
    return 1
  fi
  
  return 0
}


