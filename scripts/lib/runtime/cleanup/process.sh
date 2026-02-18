#!/usr/bin/env bash
# =============================================================================
# Runtime Cleanup - Processes
# =============================================================================

cleanup_stop_server_session() {
  local root_dir="$1"
  local pid_file="${root_dir}/server.pid"

  if [ -f "${pid_file}" ]; then
    local pid
    pid="$(cat "${pid_file}" 2>/dev/null || true)"
    if [ -n "${pid}" ] && ps -p "${pid}" >/dev/null 2>&1; then
      kill -TERM -"${pid}" || true
      for _ in {1..10}; do
        ps -p "${pid}" >/dev/null 2>&1 || break
        sleep 1
      done
      if ps -p "${pid}" >/dev/null 2>&1; then
        kill -KILL -"${pid}" || true
      fi
    fi
    rm -f "${pid_file}" || true
  else
    pkill -f "uvicorn src.server:app" || true
  fi
}

cleanup_kill_engine_processes() {
  pkill -f "vllm.v1.engine.core" || true
  pkill -f "EngineCore_0" || true
  pkill -f "python.*vllm" || true
  pkill -f "python.*tensorrt" || true
  pkill -f "python.*trtllm" || true
  pkill -f "trtllm-build" || true
  pkill -f "quantize.py" || true
  pkill -f "mpirun" || true
  pkill -f "mpi4py" || true
  pkill -f "python.*cuda" || true
}

# If GPUs are wedged, terminate every process holding a CUDA context and
# optionally trigger nvidia-smi --gpu-reset when HARD_RESET=1.
cleanup_gpu_processes() {
  local hard_reset="${1:-0}"
  command -v nvidia-smi >/dev/null 2>&1 || return 0

  local -a gpids=()
  mapfile -t gpids < <(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | awk '{print $1}' | grep -E '^[0-9]+$' || true)
  if [ "${#gpids[@]}" -gt 0 ]; then
    local p
    for p in "${gpids[@]}"; do
      kill -TERM "$p" 2>/dev/null || true
    done
    sleep 2
    for p in "${gpids[@]}"; do
      kill -KILL "$p" 2>/dev/null || true
    done
  fi

  if [ "${hard_reset}" = "1" ]; then
    nvidia-smi --gpu-reset || true
  fi
}

cleanup_server_artifacts() {
  local root_dir="$1"
  rm -f "${root_dir}/server.log" "${root_dir}/server.pid" "${root_dir}/.server.log.trim" || true
}
