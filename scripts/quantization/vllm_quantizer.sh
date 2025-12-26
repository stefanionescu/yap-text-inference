#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced helpers rely on ROOT_DIR
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${SCRIPT_DIR}/../lib/common/log.sh"

# vLLM quantization helpers
source "${SCRIPT_DIR}/../lib/env/quantization.sh"
source "${SCRIPT_DIR}/../engines/vllm/push.sh"
source "${SCRIPT_DIR}/../engines/vllm/quantize.sh"

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
vllm_awq_should_use_prequant

# Main quantization logic
vllm_awq_ensure_cache_dir

if [ "${USE_PREQUANT_AWQ}" = "1" ]; then
  if [ "${AWQ_TARGET_CHAT}" = "1" ]; then
    if ! vllm_awq_handle_chat_prequant_or_quantize; then
      log_err "[quant] ✗ AWQ quantization pipeline failed while preparing chat model; aborting."
      exit 1
    fi
  fi
else
  log_info "[quant] Running AWQ quantization process"
  if [ "${AWQ_TARGET_CHAT}" = "1" ]; then
    if ! vllm_awq_quantize_chat_if_needed; then
      log_err "[quant] ✗ AWQ quantization pipeline failed while quantizing chat model; aborting."
      exit 1
    fi
  fi
  log_info "[quant] AWQ quantization process completed"
fi
