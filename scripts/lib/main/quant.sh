#!/usr/bin/env bash
# =============================================================================
# Quantization Resolution for Main Script
# =============================================================================
# Functions to determine the appropriate quantization backend based on
# model type, user flags, and pre-quantized model detection.

_MAIN_QUANT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../config/values/core.sh
source "${_MAIN_QUANT_DIR}/../../config/values/core.sh"
# shellcheck source=../../config/values/quantization.sh
source "${_MAIN_QUANT_DIR}/../../config/values/quantization.sh"
# shellcheck source=../../config/values/model.sh
source "${_MAIN_QUANT_DIR}/../../config/values/model.sh"
# shellcheck source=../../config/patterns.sh
source "${_MAIN_QUANT_DIR}/../../config/patterns.sh"

# Resolve the 4-bit backend based on model classification
# Usage: resolve_4bit_backend <chat_model>
# Returns: "awq" or "gptq_marlin"
resolve_4bit_backend() {
  local chat_model="$1"
  if [ -z "${chat_model}" ]; then
    echo "${CFG_QUANT_MODE_4BIT_BACKEND}"
    return
  fi

  local classification
  classification="$(classify_prequant "${chat_model}")"
  case "${classification}" in
    "${CFG_MODEL_TOKEN_GPTQ}") echo "${CFG_QUANT_MODE_GPTQ_BACKEND}" ;;
    "${CFG_MODEL_TOKEN_AWQ}") echo "${CFG_QUANT_MODE_4BIT_BACKEND}" ;;
    *) echo "${CFG_QUANT_MODE_4BIT_BACKEND}" ;;
  esac
}

# Apply quantization selection based on user flags and model hints
# Usage: quant_resolve_settings <deploy_mode> <chat_model> <forced_mode> <chat_hint> [current_chat_quant]
# Sets: QUANT_MODE, CHAT_QUANTIZATION
quant_resolve_settings() {
  local deploy_mode="$1"
  local chat_model="$2"
  local forced_mode="${3:-${CFG_QUANT_MODE_AUTO}}"
  local chat_hint="${4:-}"
  local current_chat_quant="${5:-}"

  if [ "${deploy_mode}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    QUANT_MODE="${CFG_QUANT_MODE_TOOL_ONLY}"
    unset CHAT_QUANTIZATION
    export QUANT_MODE
    return
  fi

  local resolved_backend=""
  local resolved_mode=""

  if [ -n "${current_chat_quant}" ]; then
    resolved_backend="${current_chat_quant}"
  fi

  if [ -z "${resolved_backend}" ]; then
    case "${forced_mode}" in
      "${CFG_QUANT_MODE_4BIT_PLACEHOLDER}")
        resolved_mode="${CFG_QUANT_MODE_4BIT_PLACEHOLDER}"
        resolved_backend="$(resolve_4bit_backend "${chat_model}")"
        ;;
      "${CFG_QUANT_MODE_8BIT_PLACEHOLDER}")
        resolved_mode="${CFG_QUANT_MODE_8BIT_PLACEHOLDER}"
        resolved_backend="${CFG_QUANT_MODE_8BIT_PLACEHOLDER}"
        ;;
      "${CFG_QUANT_MODE_AUTO}" | "")
        if [ -n "${chat_hint}" ]; then
          resolved_mode="${CFG_QUANT_MODE_4BIT_PLACEHOLDER}"
          resolved_backend="${chat_hint}"
        else
          resolved_mode="${CFG_QUANT_MODE_8BIT_PLACEHOLDER}"
          resolved_backend="${CFG_QUANT_MODE_8BIT_PLACEHOLDER}"
        fi
        ;;
      *)
        resolved_backend="${forced_mode}"
        ;;
    esac
  fi

  if [ -n "${chat_model}" ]; then
    local prequant_kind
    prequant_kind="$(classify_prequant "${chat_model}")"
    case "${prequant_kind}" in
      "${CFG_MODEL_TOKEN_AWQ}")
        if [ "${resolved_backend}" != "${CFG_QUANT_MODE_4BIT_BACKEND}" ]; then
          log_warn "[quant] ⚠ Chat model '${chat_model}' is already 4-bit (AWQ/W4A16); overriding to 4bit runtime."
          resolved_mode="${CFG_QUANT_MODE_4BIT_PLACEHOLDER}"
          resolved_backend="${CFG_QUANT_MODE_4BIT_BACKEND}"
        fi
        ;;
      "${CFG_MODEL_TOKEN_GPTQ}")
        if [ "${resolved_backend}" != "${CFG_QUANT_MODE_GPTQ_BACKEND}" ]; then
          log_warn "[quant] ⚠ Chat model '${chat_model}' is GPTQ; overriding to 4bit GPTQ runtime."
          resolved_mode="${CFG_QUANT_MODE_4BIT_PLACEHOLDER}"
          resolved_backend="${CFG_QUANT_MODE_GPTQ_BACKEND}"
        fi
        ;;
    esac
  fi

  if [ -z "${resolved_backend}" ]; then
    resolved_backend="${CFG_QUANT_MODE_8BIT_PLACEHOLDER}"
  fi

  if [ -z "${resolved_mode}" ]; then
    case "${resolved_backend}" in
      "${CFG_QUANT_MODE_4BIT_BACKEND}" | "${CFG_QUANT_MODE_GPTQ_ALIAS}" | "${CFG_QUANT_MODE_GPTQ_BACKEND}" | "${CFG_QUANT_MODE_4BIT_PLACEHOLDER}")
        resolved_mode="${CFG_QUANT_MODE_4BIT_PLACEHOLDER}"
        ;;
      *)
        resolved_mode="${CFG_QUANT_MODE_8BIT_PLACEHOLDER}"
        ;;
    esac
  fi

  QUANT_MODE="${resolved_mode}"
  CHAT_QUANTIZATION="${resolved_backend}"
  export QUANT_MODE CHAT_QUANTIZATION
}

# Apply quantization selection based on user flags and model hints
# Usage: apply_quantization <forced_mode> <chat_hint>
apply_quantization() {
  quant_resolve_settings \
    "${DEPLOY_MODE:-}" \
    "${CHAT_MODEL_NAME:-}" \
    "${1:-${CFG_QUANT_MODE_AUTO}}" \
    "${2:-}" \
    "${CHAT_QUANTIZATION:-}"
}

# Get quantization hint from chat model name
# Usage: get_quant_hint
# Returns: quantization hint or empty string
get_quant_hint() {
  if [ "${DEPLOY_MODE:-}" != "${CFG_DEPLOY_MODE_TOOL}" ] && [ -z "${CHAT_QUANTIZATION:-}" ]; then
    get_quantization_hint "${CHAT_MODEL_NAME:-}"
  fi
}
