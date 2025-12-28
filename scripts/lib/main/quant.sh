#!/usr/bin/env bash
# Quantization resolution for main.sh
#
# Functions to determine the appropriate quantization backend
# based on model type, user flags, and pre-quantized model detection.

# Resolve the 4-bit backend based on model classification
# Usage: main_resolve_4bit_backend <chat_model>
# Returns: "awq" or "gptq_marlin"
main_resolve_4bit_backend() {
  local chat_model="$1"
  if [ -z "${chat_model}" ]; then
    echo "awq"
    return
  fi

  local classification
  classification="$(model_detect_classify_prequant "${chat_model}")"
  case "${classification}" in
    gptq) echo "gptq_marlin" ;;
    awq) echo "awq" ;;
    *) echo "awq" ;;
  esac
}

# Apply quantization selection based on user flags and model hints
# Usage: main_apply_quantization <forced_mode> <chat_hint>
# Sets: QUANT_MODE, QUANTIZATION, CHAT_QUANTIZATION
main_apply_quantization() {
  local forced_mode="$1"
  local chat_hint="$2"

  # Tool-only mode: no quantization needed
  if [ "${DEPLOY_MODE_SELECTED}" = "tool" ]; then
    QUANT_MODE="tool-only"
    unset QUANTIZATION
    unset CHAT_QUANTIZATION
    export QUANT_MODE
    return
  fi

  local resolved_mode=""
  local resolved_backend=""

  case "${forced_mode}" in
    4bit)
      resolved_mode="4bit"
      resolved_backend="$(main_resolve_4bit_backend "${CHAT_MODEL_NAME}")"
      ;;
    8bit)
      resolved_mode="8bit"
      # Backend (fp8 vs int8) is resolved later based on GPU architecture
      resolved_backend="8bit"
      ;;
    auto)
      if [ -n "${chat_hint:-}" ]; then
        resolved_mode="4bit"
        resolved_backend="${chat_hint}"
      else
        resolved_mode="8bit"
        # Backend (fp8 vs int8) is resolved later based on GPU architecture
        resolved_backend="8bit"
      fi
      ;;
    *)
      resolved_mode="8bit"
      # Backend (fp8 vs int8) is resolved later based on GPU architecture
      resolved_backend="8bit"
      ;;
  esac

  # Check for pre-quantized models and override if needed
  if [ "${DEPLOY_MODE_SELECTED}" != "tool" ]; then
    local prequant_kind
    prequant_kind="$(model_detect_classify_prequant "${CHAT_MODEL_NAME}")"
    case "${prequant_kind}" in
      awq)
        if [ "${resolved_backend}" != "awq" ]; then
          log_warn "[quant] ⚠ Chat model '${CHAT_MODEL_NAME}' is already 4-bit (AWQ/W4A16); overriding to 4bit runtime."
          resolved_mode="4bit"
          resolved_backend="awq"
        fi
        ;;
      gptq)
        if [ "${resolved_backend}" != "gptq_marlin" ]; then
          log_warn "[quant] ⚠ Chat model '${CHAT_MODEL_NAME}' is GPTQ; overriding to 4bit GPTQ runtime."
          resolved_mode="4bit"
          resolved_backend="gptq_marlin"
        fi
        ;;
    esac
  fi

  QUANT_MODE="${resolved_mode}"
  QUANTIZATION="${resolved_backend}"
  if [ "${DEPLOY_MODE_SELECTED}" != "tool" ]; then
    CHAT_QUANTIZATION="${resolved_backend}"
  fi

  export QUANT_MODE QUANTIZATION
  if [ -n "${CHAT_QUANTIZATION:-}" ]; then
    export CHAT_QUANTIZATION
  fi
}

# Get quantization hint from chat model name
# Usage: main_get_quant_hint
# Returns: quantization hint or empty string
main_get_quant_hint() {
  if [ "${DEPLOY_MODE_SELECTED}" != "tool" ] && [ -z "${CHAT_QUANTIZATION:-}" ]; then
    model_detect_quantization_hint "${CHAT_MODEL_NAME}"
  fi
}

