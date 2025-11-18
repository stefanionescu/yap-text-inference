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

# If not using AWQ, do nothing and stay silent (no logs)
# shellcheck disable=SC2317  # pattern handles sourced vs executed scripts
if [ "${QUANTIZATION:-}" != "awq" ]; then
  return 0 2>/dev/null || exit 0
fi

log_info "Running AWQ quantization process"
awq_setup_hf_env

awq_should_use_prequant
if [ "${USE_PREQUANT_AWQ}" = "1" ]; then
  log_info "Using pre-quantized AWQ models from Hugging Face (when available)"
fi

# Main quantization logic (QUANTIZATION=awq guaranteed by early guard)
if [ "${QUANTIZATION}" = "awq" ]; then
  awq_ensure_cache_dir

  if [ "${USE_PREQUANT_AWQ}" = "1" ]; then
    # Pre-quantized models when provided, otherwise quantize locally
    if [ "${DEPLOY_TOOL}" = "1" ]; then
      awq_handle_tool_prequant_or_quantize
    fi
    if [ "${DEPLOY_CHAT}" = "1" ]; then
      awq_handle_chat_prequant_or_quantize
    fi
  else
    log_info "Starting local AWQ quantization process"
    if [ "${DEPLOY_TOOL}" = "1" ]; then
      awq_quantize_tool_if_needed
    fi
    if [ "${DEPLOY_CHAT}" = "1" ]; then
      awq_quantize_chat_if_needed
    fi
  fi
fi

log_info "AWQ quantization process completed"