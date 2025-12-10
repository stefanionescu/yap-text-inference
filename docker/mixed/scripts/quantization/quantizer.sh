#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # sourced AWQ helpers rely on ROOT_DIR
ROOT_DIR="/app"
source "${SCRIPT_DIR}/../logs.sh"

# Only act for AWQ
# shellcheck disable=SC2317  # pattern handles sourced vs executed scripts
if [ "${QUANTIZATION:-}" != "awq" ]; then
  return 0 2>/dev/null || exit 0
fi

if [ "${DEPLOY_TOOL:-0}" = "1" ]; then
  if [ "${TOOL_QUANTIZATION:-}" = "awq" ] || { [ -z "${TOOL_QUANTIZATION:-}" ] && [ "${QUANTIZATION:-}" = "awq" ]; }; then
    log_error "Tool models are classifier-only; AWQ quantization is not supported."
    exit 1
  fi
fi

log_info "Running AWQ quantization process (Docker Base)"

## Respect pre-quantized setups strictly: if the chat engine is already AWQ,
## do not perform any additional quantization.
# shellcheck disable=SC2317  # pattern handles sourced vs executed scripts
if [ "${CHAT_QUANTIZATION:-}" = "awq" ]; then
  log_info "Detected pre-quantized AWQ chat model; skipping runtime quantization to honor existing setup"
  return 0 2>/dev/null || exit 0
fi

# Source modular AWQ components
source "${SCRIPT_DIR}/awq/deps.sh"
source "${SCRIPT_DIR}/awq/push.sh"
source "${SCRIPT_DIR}/awq/quantize_core.sh"
source "${SCRIPT_DIR}/awq/resolve.sh"

log_info "AWQ quantization process completed"

