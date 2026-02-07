#!/usr/bin/env bash
# =============================================================================
# Quantization Resolution for Main Script
# =============================================================================
# Functions to determine the appropriate quantization backend based on
# model type, user flags, and pre-quantized model detection.

# Resolve the 4-bit backend based on model classification
# Usage: resolve_4bit_backend <chat_model>
# Returns: "awq" or "gptq_marlin"
resolve_4bit_backend() {
  local chat_model="$1"
  if [ -z "${chat_model}" ]; then
    echo "awq"
    return
  fi

  local classification
  classification="$(classify_prequant "${chat_model}")"
  case "${classification}" in
    gptq) echo "gptq_marlin" ;;
    awq) echo "awq" ;;
    *) echo "awq" ;;
  esac
}

# Apply quantization selection based on user flags and model hints
# Usage: quant_resolve_settings <deploy_mode> <chat_model> <forced_mode> <chat_hint> [current_chat_quant]
# Sets: QUANT_MODE, CHAT_QUANTIZATION
quant_resolve_settings() {
  local deploy_mode="$1"
  local chat_model="$2"
  local forced_mode="${3:-auto}"
  local chat_hint="${4:-}"
  local current_chat_quant="${5:-}"

  if [ "${deploy_mode}" = "tool" ]; then
    QUANT_MODE="tool-only"
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
      4bit)
        resolved_mode="4bit"
        resolved_backend="$(resolve_4bit_backend "${chat_model}")"
        ;;
      8bit)
        resolved_mode="8bit"
        resolved_backend="8bit"
        ;;
      auto | "")
        if [ -n "${chat_hint}" ]; then
          resolved_mode="4bit"
          resolved_backend="${chat_hint}"
        else
          resolved_mode="8bit"
          resolved_backend="8bit"
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
      awq)
        if [ "${resolved_backend}" != "awq" ]; then
          log_warn "[quant] ⚠ Chat model '${chat_model}' is already 4-bit (AWQ/W4A16); overriding to 4bit runtime."
          resolved_mode="4bit"
          resolved_backend="awq"
        fi
        ;;
      gptq)
        if [ "${resolved_backend}" != "gptq_marlin" ]; then
          log_warn "[quant] ⚠ Chat model '${chat_model}' is GPTQ; overriding to 4bit GPTQ runtime."
          resolved_mode="4bit"
          resolved_backend="gptq_marlin"
        fi
        ;;
    esac
  fi

  if [ -z "${resolved_backend}" ]; then
    resolved_backend="8bit"
  fi

  if [ -z "${resolved_mode}" ]; then
    case "${resolved_backend}" in
      awq | gptq | gptq_marlin | 4bit)
        resolved_mode="4bit"
        ;;
      *)
        resolved_mode="8bit"
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
    "${1:-auto}" \
    "${2:-}" \
    "${CHAT_QUANTIZATION:-}"
}

# Get quantization hint from chat model name
# Usage: get_quant_hint
# Returns: quantization hint or empty string
get_quant_hint() {
  if [ "${DEPLOY_MODE:-}" != "tool" ] && [ -z "${CHAT_QUANTIZATION:-}" ]; then
    get_quantization_hint "${CHAT_MODEL_NAME:-}"
  fi
}
