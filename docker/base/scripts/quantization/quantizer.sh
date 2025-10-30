#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="/app"
source "${SCRIPT_DIR}/../common/utils.sh"

# Only act for AWQ
if [ "${QUANTIZATION:-}" != "awq" ]; then
  return 0 2>/dev/null || exit 0
fi

log_info "Running AWQ quantization process (Docker Base)"

## Respect pre-quantized setups strictly: if either engine is already AWQ,
## do not perform any additional quantization. We "run like that" and skip.
if [ "${CHAT_QUANTIZATION:-}" = "awq" ] || [ "${TOOL_QUANTIZATION:-}" = "awq" ]; then
  log_info "Detected pre-quantized AWQ for at least one model; skipping runtime quantization to honor existing setup"
  return 0 2>/dev/null || exit 0
fi

# Source modular AWQ components
source "${SCRIPT_DIR}/awq/deps.sh"
source "${SCRIPT_DIR}/awq/push.sh"
source "${SCRIPT_DIR}/awq/quantize_core.sh"
source "${SCRIPT_DIR}/awq/resolve.sh"

log_info "AWQ quantization process completed"

