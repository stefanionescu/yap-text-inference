#!/usr/bin/env bash

# Helpers shared by main.sh and restart.sh for log rotation and background launches.

_RUNTIME_PIPELINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prepare server.log for a new run, trimming oversized files and ensuring the
# .run directory exists so downstream helpers can rely on pid/log state.
runtime_pipeline_prepare_log() {
  local root_dir="${1:-${ROOT_DIR:-}}"
  local server_log="${root_dir}/server.log"
  mkdir -p "${root_dir}/.run"

  if [ -f "${server_log}" ]; then
    local max_keep_bytes=$((100 * 1024 * 1024))  # 100MB
    local size
    size=$(wc -c <"${server_log}" 2>/dev/null || echo 0)
    if [ "${size}" -gt "${max_keep_bytes}" ]; then
      local offset=$((size - max_keep_bytes))
      local tmp_file="${root_dir}/.server.log.trim"
      if tail -c "${max_keep_bytes}" "${server_log}" > "${tmp_file}" 2>/dev/null; then
        mv "${tmp_file}" "${server_log}" 2>/dev/null || true
        echo "[server] Trimmed server.log to latest 100MB (removed ${offset} bytes)" >> "${server_log}"
      fi
    fi
  fi

  echo "${server_log}"
}

# Launch the composed deployment command inside a detached session.
# Args:
#   $1 - repo root (used for pid/log files)
#   $2 - command string to execute (typically the pipeline chain)
#   $3 - follow flag (1 tails server log, 0 returns immediately)
#   $4 - log prefix describing what is being launched
runtime_pipeline_run_background() {
  local root_dir="$1"
  local command_string="$2"
  local follow_logs="${3:-1}"
  local start_message="${4:-Starting background deployment...}"

  local server_log
  server_log="$(runtime_pipeline_prepare_log "${root_dir}")"

  log_info "[main] ${start_message}"
  log_info "[main] Ctrl+C after launch stops log tail only; deployment keeps running."

  setsid nohup bash -lc "${command_string}" </dev/null > "${server_log}" 2>&1 &
  local bg_pid=$!
  echo "${bg_pid}" > "${root_dir}/.run/deployment.pid"

  log_info "[main] Deployment started (PID: ${bg_pid})"
  log_info "[main] All logs (deployment + server): ${server_log}"
  log_info "[main] To stop: bash scripts/stop.sh"

  if [ "${follow_logs}" = "1" ]; then
    log_blank
    touch "${server_log}" || true
    local warmup_lock="${root_dir}/.run/warmup.lock"
    local warmup_capture="${root_dir}/logs/warmup.server.log"
    exec "${_RUNTIME_PIPELINE_DIR}/follow_logs.sh" "${server_log}" "${warmup_lock}" "${warmup_capture}"
  fi
}
