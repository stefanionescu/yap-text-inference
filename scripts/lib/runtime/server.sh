#!/usr/bin/env bash
# =============================================================================
# Server Lifecycle Management
# =============================================================================
# Functions for starting, stopping, and managing the uvicorn server process.
# Handles PID file management, health checks, and uvicorn binary resolution.

# =============================================================================
# PID FILE MANAGEMENT
# =============================================================================

# Check for existing server process and handle stale PID files.
# Returns 0 if safe to start, exits with 1 if server already running.
# Usage: guard_check_pid <root_dir>
guard_check_pid() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  local pid_file="${root_dir}/server.pid"

  if [ ! -f "${pid_file}" ]; then
    return 0
  fi

  local old_pid
  old_pid="$(cat "${pid_file}" 2>/dev/null || true)"

  if [ -n "${old_pid}" ] && ps -p "${old_pid}" >/dev/null 2>&1; then
    log_warn "[server] ⚠ Server already running (PID=${old_pid}). Aborting start."
    exit 1
  fi

  log_warn "[server] ⚠ Stale PID file found; removing ${pid_file}"
  rm -f "${pid_file}" || true
  return 0
}

# Write server PID to file after starting.
# Usage: write_pid <root_dir> <pid>
write_pid() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  local pid="$2"
  echo "${pid}" >"${root_dir}/server.pid"
}

# Kill server process and clean up PID file.
# Usage: kill_and_cleanup <root_dir>
kill_and_cleanup() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  local pid_file="${root_dir}/server.pid"

  if [ -f "${pid_file}" ]; then
    kill -TERM "-$(cat "${pid_file}")" 2>/dev/null || true
    rm -f "${pid_file}"
  fi
}

# =============================================================================
# CONFIGURATION LOGGING
# =============================================================================

# Read kv_cache_dtype from TRT engine build metadata.
# For TRT-LLM, KV cache dtype is baked into the engine at build time and
# cannot be changed at runtime. The KV_DTYPE env var is ignored by TRT.
# Returns: kv_cache_dtype value, or empty string on failure
# Usage: kv_dtype=$(_read_trt_kv_dtype "/path/to/engine")
_read_trt_kv_dtype() {
  local engine_dir="${1:-}"
  local metadata_file="${engine_dir}/build_metadata.json"

  if [ ! -f "${metadata_file}" ]; then
    return 0
  fi

  python3 -c "
import json
with open('${metadata_file}') as f:
    print(json.load(f).get('kv_cache_dtype', ''))
" 2>/dev/null || true
}

# Log current deployment configuration.
# Usage: log_server_config
log_server_config() {
  local deploy_mode="${DEPLOY_MODE:-both}"

  case "${deploy_mode}" in
    both)
      log_info "[server]   CHAT=${CHAT_MODEL:-}"
      log_info "[server]   TOOL=${TOOL_MODEL:-}"
      ;;
    chat)
      log_info "[server]   MODEL=${CHAT_MODEL:-}"
      ;;
    tool)
      log_info "[server]   MODEL=${TOOL_MODEL:-}"
      ;;
  esac

  if [ "${deploy_mode}" = "tool" ]; then
    log_info "[server]   QUANT_MODE=tool-only (classifier-only)"
  else
    log_info "[server]   QUANT_MODE=${QUANT_MODE:-auto}"
    log_info "[server]   CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-auto}"

    # For TRT: show the actual KV dtype baked into the engine
    # For vLLM: show the KV_DTYPE env var (which vLLM uses at runtime)
    local kv_dtype_display="${KV_DTYPE:-}"
    local kv_dtype_source=""

    if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ] && [ -n "${TRT_ENGINE_DIR:-}" ]; then
      local engine_kv_dtype
      engine_kv_dtype="$(_read_trt_kv_dtype "${TRT_ENGINE_DIR}")"
      if [ -n "${engine_kv_dtype}" ]; then
        kv_dtype_display="${engine_kv_dtype}"
        kv_dtype_source=" [from engine]"
      fi
    fi

    log_info "[server]   KV_DTYPE=${kv_dtype_display}${kv_dtype_source}"
  fi
}

# =============================================================================
# UVICORN RESOLUTION
# =============================================================================

# Resolve the uvicorn command to use.
# Tries: venv python -m uvicorn, venv uvicorn, system uvicorn, system python -m uvicorn
# Sets SERVER_CMD array with the command to run.
# Usage: resolve_uvicorn <venv_dir>
# Returns: 0 on success, 127 if uvicorn not found
resolve_uvicorn() {
  local venv_dir="${1:-${VENV_DIR:-}}"

  SERVER_CMD_ARGS=(
    "src.server:app"
    "--host" "${SERVER_BIND_HOST}"
    "--port" "${SERVER_PORT}"
    "--workers" "1"
  )

  # Try venv python -m uvicorn first (most reliable)
  if [ -x "${venv_dir}/bin/python" ] && "${venv_dir}/bin/python" -c "import uvicorn" >/dev/null 2>&1; then
    SERVER_CMD=("${venv_dir}/bin/python" "-m" "uvicorn" "${SERVER_CMD_ARGS[@]}")
    return 0
  fi

  # Try venv uvicorn binary
  if [ -x "${venv_dir}/bin/uvicorn" ]; then
    SERVER_CMD=("${venv_dir}/bin/uvicorn" "${SERVER_CMD_ARGS[@]}")
    return 0
  fi

  # Try system uvicorn
  if command -v uvicorn >/dev/null 2>&1; then
    SERVER_CMD=("$(command -v uvicorn)" "${SERVER_CMD_ARGS[@]}")
    return 0
  fi

  # Try system python3 -m uvicorn
  if command -v python3 >/dev/null 2>&1 && python3 -c "import uvicorn" >/dev/null 2>&1; then
    SERVER_CMD=("python3" "-m" "uvicorn" "${SERVER_CMD_ARGS[@]}")
    return 0
  fi

  # Try system python -m uvicorn
  if command -v python >/dev/null 2>&1 && python -c "import uvicorn" >/dev/null 2>&1; then
    SERVER_CMD=("python" "-m" "uvicorn" "${SERVER_CMD_ARGS[@]}")
    return 0
  fi

  log_err "[server] ✗ uvicorn is not installed in venv (${venv_dir}) or system."
  log_err "[server] ✗ Run: bash scripts/steps/03_install_deps.sh"
  return 127
}

# =============================================================================
# HEALTH CHECKS
# =============================================================================

# Wait for server to become healthy with timeout.
# Uses SERVER_LOCAL_HEALTH_URLS (localhost) for internal health checks.
# Usage: await_server_health
# Returns: 0 if healthy, 1 if timeout
await_server_health() {
  local deadline=$((SECONDS + WARMUP_TIMEOUT_SECS))
  local urls=("${SERVER_LOCAL_HEALTH_URLS[@]}")

  while ((SECONDS <= deadline)); do
    if bash "${WARMUP_HEALTH_CHECK_SCRIPT}" "${urls[@]}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${WARMUP_HEALTH_POLL_INTERVAL_SECS}"
  done

  return 1
}

# =============================================================================
# SERVER LIFECYCLE
# =============================================================================

# Start the server in the background as a new session.
# Usage: start_background <root_dir>
# Sets: SERVER_PID with the started process ID
start_background() {
  local root_dir="${1:-${ROOT_DIR:-}}"

  # Start as a new session so Ctrl+C in the calling shell won't touch it
  setsid "${SERVER_CMD[@]}" >>"${root_dir}/server.log" 2>&1 &
  SERVER_PID=$!
  write_pid "${root_dir}" "${SERVER_PID}"
}

# Log server startup success information.
# Usage: log_started <root_dir>
log_started() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  local health_hint="${SERVER_HEALTH_URLS[0]:-http://${SERVER_ADDR}/healthz}"

  log_info "[server] ✓ Server started"
  log_info "[server] Health: curl -s ${health_hint}"
  log_info "[server] All logs: tail -f ${root_dir}/server.log"
  log_info "[server] Stop: kill -TERM -$(cat "${root_dir}/server.pid")"
  log_blank
}

# Handle server startup failure (health check timeout).
# Usage: handle_startup_failure <root_dir>
handle_startup_failure() {
  local root_dir="${1:-${ROOT_DIR:-}}"

  log_err "[server] ✗ Server did not become healthy within ${WARMUP_TIMEOUT_SECS}s"
  log_err "[server] Check logs: tail -f ${root_dir}/server.log"
  kill_and_cleanup "${root_dir}"
  exit 1
}

# =============================================================================
# WARMUP
# =============================================================================

# Run the warmup script if available.
# Usage: run_warmup <root_dir>
run_warmup() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  local warmup_script="${root_dir}/scripts/warmup.sh"

  if [ -x "${warmup_script}" ]; then
    log_info "[warmup] Running warmup validation script..."
    if ! "${warmup_script}"; then
      log_warn "[warmup] ⚠ Warmup script detected issues (see logs/warmup.log)"
    fi
  else
    log_warn "[warmup] ⚠ Warmup script not found at ${warmup_script}"
  fi
}
