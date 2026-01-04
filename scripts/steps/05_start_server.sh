#!/usr/bin/env bash
# =============================================================================
# Server Startup Script
# =============================================================================
# Starts the uvicorn server in the background and runs warmup validation.
# All server lifecycle logic is delegated to lib/runtime/server.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Source dependencies
source "${SCRIPT_DIR}/../lib/noise/python.sh"
source "${SCRIPT_DIR}/../lib/common/log.sh"
source "${SCRIPT_DIR}/../lib/runtime/restart_guard.sh"
source "${SCRIPT_DIR}/../lib/runtime/server.sh"
source "${SCRIPT_DIR}/../lib/deps/venv.sh"
source "${SCRIPT_DIR}/../engines/trt/detect.sh"
source "${SCRIPT_DIR}/../lib/common/cuda.sh"
source "${SCRIPT_DIR}/../lib/env/server.sh"
source "${SCRIPT_DIR}/../lib/env/warmup.sh"

# =============================================================================
# MAIN
# =============================================================================

# Validate CUDA 13.x for TRT before starting server
ensure_cuda_ready_for_engine "server" || exit 1

# Initialize network and warmup configuration
init_network_defaults
init_warmup_defaults "${ROOT_DIR}" "${SCRIPT_DIR}/.."

log_info "[server] Starting server on ${SERVER_BIND_ADDR} in background"
cd "${ROOT_DIR}"

# Activate venv if available (non-fatal)
activate_venv "" 0 || true
VENV_DIR="$(get_venv_dir)"

# Check for existing server process
guard_check_pid "${ROOT_DIR}"

# Log current configuration
log_server_config
log_blank

# Write config snapshot for restart detection
write_snapshot "${ROOT_DIR}"

# Resolve uvicorn command
if ! resolve_uvicorn "${VENV_DIR}"; then
  exit 127
fi

# Start server in background
start_background "${ROOT_DIR}"

log_info "[server] Waiting for server to become healthy (timeout ${WARMUP_TIMEOUT_SECS}s)..."

# Wait for health and handle failure
if ! await_server_health; then
  handle_startup_failure "${ROOT_DIR}"
fi

# Log success and run warmup
log_started "${ROOT_DIR}"
run_warmup "${ROOT_DIR}"
