#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced helpers rely on ROOT_DIR
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${SCRIPT_DIR}/../lib/common/log.sh"

# Quantization helpers
LIB_Q="${SCRIPT_DIR}/../lib/quant"
source "${LIB_Q}/env.sh"
source "${LIB_Q}/push.sh"
source "${LIB_Q}/ops.sh"

_awq_quant_fail() {
  log_error "AWQ quantization pipeline failed; aborting."
  return 1 2>/dev/null || exit 1
}

# Determine which engines requested AWQ
AWQ_TARGET_CHAT=0
AWQ_TARGET_TOOL=0
if [ "${DEPLOY_CHAT:-0}" = "1" ]; then
  if [ "${CHAT_QUANTIZATION:-}" = "awq" ]; then
    AWQ_TARGET_CHAT=1
  elif [ -z "${CHAT_QUANTIZATION:-}" ] && [ "${QUANTIZATION:-}" = "awq" ]; then
    AWQ_TARGET_CHAT=1
  fi
fi
if [ "${DEPLOY_TOOL:-0}" = "1" ]; then
  if [ "${TOOL_QUANTIZATION:-}" = "awq" ]; then
    AWQ_TARGET_TOOL=1
  elif [ -z "${TOOL_QUANTIZATION:-}" ] && [ "${QUANTIZATION:-}" = "awq" ]; then
    AWQ_TARGET_TOOL=1
  fi
fi
export AWQ_TARGET_CHAT AWQ_TARGET_TOOL

# If neither engine needs AWQ work, exit quietly
# shellcheck disable=SC2317  # pattern handles sourced vs executed scripts
if [ "${AWQ_TARGET_CHAT}" = "0" ] && [ "${AWQ_TARGET_TOOL}" = "0" ]; then
  return 0 2>/dev/null || exit 0
fi

log_info "Running AWQ quantization process (chat=${AWQ_TARGET_CHAT}, tool=${AWQ_TARGET_TOOL})"
awq_setup_hf_env

awq_should_use_prequant
if [ "${USE_PREQUANT_AWQ}" = "1" ]; then
  log_info "Using pre-quantized AWQ models from Hugging Face (when available)"
fi

# Main quantization logic
awq_ensure_cache_dir

if [ "${USE_PREQUANT_AWQ}" = "1" ]; then
  # Pre-quantized models when provided, otherwise quantize locally
  if [ "${AWQ_TARGET_TOOL}" = "1" ]; then
    awq_handle_tool_prequant_or_quantize || _awq_quant_fail
  fi
  if [ "${AWQ_TARGET_CHAT}" = "1" ]; then
    awq_handle_chat_prequant_or_quantize || _awq_quant_fail
  fi
else
  log_info "Starting local AWQ quantization process"
  if [ "${AWQ_TARGET_TOOL}" = "1" ]; then
    awq_quantize_tool_if_needed || _awq_quant_fail
  fi
  if [ "${AWQ_TARGET_CHAT}" = "1" ]; then
    awq_quantize_chat_if_needed || _awq_quant_fail
  fi
fi

log_info "AWQ quantization process completed"