#!/usr/bin/env bash
# shellcheck disable=SC1091
set -euo pipefail

source "/app/common/scripts/logs.sh"
source "/app/common/scripts/server.sh"

cd /app
ROOT_DIR="${ROOT_DIR:-/app}"

# ============================================================================
# Validate engine exists
# ============================================================================
validate_engine() {
  local engine_dir="${TRT_ENGINE_DIR:-/opt/engines/trt-chat}"

  if [ "${DEPLOY_CHAT}" != "1" ]; then
    return 0
  fi

  if [ ! -f "${engine_dir}/rank0.engine" ]; then
    log_err "[trt] ✗ TRT engine not found at ${engine_dir}/rank0.engine"
    log_err "[trt]   This image is fail-fast: rebuild with baked artifacts or mount a valid TRT_ENGINE_DIR."
    return 1
  fi

  log_success "[trt] ✓ TRT engine validated"
}

# ============================================================================
# Main execution
# ============================================================================

# Validate engine
if ! validate_engine; then
  exit 1
fi

start_server_with_warmup "trt" "/app/common/scripts/warmup.sh" "${ROOT_DIR}"
