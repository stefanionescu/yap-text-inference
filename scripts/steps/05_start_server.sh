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
server_init_network_defaults
warmup_init_defaults "${ROOT_DIR}" "${SCRIPT_DIR}/.."

log_info "[server] Starting server on ${SERVER_BIND_ADDR} in background"
cd "${ROOT_DIR}"

# Activate venv if available (non-fatal)
activate_venv "" 0 || true
VENV_DIR="$(get_venv_dir)"

# Check for existing server process
server_guard_check_pid "${ROOT_DIR}"

# Log current configuration
server_log_config
log_blank

# Write config snapshot for restart detection
runtime_guard_write_snapshot "${ROOT_DIR}"

# Resolve uvicorn command
if ! server_resolve_uvicorn "${VENV_DIR}"; then
  exit 127
fi

# Start server in background
server_start_background "${ROOT_DIR}"

log_info "[server] Waiting for server to become healthy (timeout ${WARMUP_TIMEOUT_SECS}s)..."

# Wait for health and handle failure
if ! server_wait_for_health; then
  server_handle_startup_failure "${ROOT_DIR}"
fi

# Log success and run warmup
server_log_started "${ROOT_DIR}"
server_run_warmup "${ROOT_DIR}"
