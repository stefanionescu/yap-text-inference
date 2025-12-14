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

# Determine which engines requested AWQ
AWQ_TARGET_CHAT=0
if [ "${DEPLOY_CHAT:-0}" = "1" ]; then
  if [ "${CHAT_QUANTIZATION:-}" = "awq" ]; then
    AWQ_TARGET_CHAT=1
  elif [ -z "${CHAT_QUANTIZATION:-}" ] && [ "${QUANTIZATION:-}" = "awq" ]; then
    AWQ_TARGET_CHAT=1
  fi
fi

export AWQ_TARGET_CHAT

# If neither engine needs AWQ work, exit quietly
# shellcheck disable=SC2317  # pattern handles sourced vs executed scripts
if [ "${AWQ_TARGET_CHAT}" = "0" ]; then
  return 0 2>/dev/null || exit 0
fi

awq_setup_hf_env
awq_should_use_prequant

# Main quantization logic
awq_ensure_cache_dir

if [ "${USE_PREQUANT_AWQ}" = "1" ]; then
  if [ "${AWQ_TARGET_CHAT}" = "1" ]; then
    if ! awq_handle_chat_prequant_or_quantize; then
      log_error "AWQ quantization pipeline failed while preparing chat model; aborting."
      exit 1
    fi
  fi
else
  log_info "Running AWQ quantization process"
  if [ "${AWQ_TARGET_CHAT}" = "1" ]; then
    if ! awq_quantize_chat_if_needed; then
      log_error "AWQ quantization pipeline failed while quantizing chat model; aborting."
      exit 1
    fi
  fi
  log_info "AWQ quantization process completed"
fi