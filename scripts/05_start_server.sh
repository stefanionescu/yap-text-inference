#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Starting server on :8000 in background"
cd "${ROOT_DIR}"
if [ -d "${ROOT_DIR}/.venv" ]; then
  source "${ROOT_DIR}/.venv/bin/activate"
fi

# Double-start guard and stale PID handling
PID_FILE="${ROOT_DIR}/server.pid"
if [ -f "${PID_FILE}" ]; then
  OLD_PID="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [ -n "${OLD_PID}" ] && ps -p "${OLD_PID}" >/dev/null 2>&1; then
    log_warn "Server already running (PID=${OLD_PID}). Aborting start."
    exit 1
  else
    log_warn "Stale PID file found; removing ${PID_FILE}"
    rm -f "${PID_FILE}" || true
  fi
fi

# Log key env knobs
log_info "GPU=${DETECTED_GPU_NAME:-unknown} MODEL=${CHAT_MODEL:-} QUANTIZATION=${QUANTIZATION:-} KV_DTYPE=${KV_DTYPE:-}"
log_info "DEPLOY_MODELS=${DEPLOY_MODELS:-both} CHAT=${CHAT_MODEL:-} TOOL=${TOOL_MODEL:-}"
log_info "TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-} VLLM_USE_V1=${VLLM_USE_V1:-} ENFORCE_EAGER=${ENFORCE_EAGER:-}"

# Start as a new session so Ctrl+C in the calling shell won't touch it.
# Write the session leader PID so we can kill the whole tree later.
# Append to server.log to continue the unified deployment+server log
setsid uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1 >> "${ROOT_DIR}/server.log" 2>&1 &
SERVER_PID=$!
echo "${SERVER_PID}" > "${ROOT_DIR}/server.pid"

log_info "Server started: PID=$(cat "${ROOT_DIR}/server.pid")"
log_info "Health:  curl -s http://127.0.0.1:8000/healthz"
log_info "All logs: tail -f ${ROOT_DIR}/server.log"
log_info "Stop:    kill -TERM -$(cat ${ROOT_DIR}/server.pid)  # negative PID kills session"

# Optional warmup to prefill KV, kernels, tokenizer
if [ "${WARMUP_ON_START:-1}" = "1" ]; then
  log_info "Running warmup client"
  RECV_TIMEOUT_SEC=${RECV_TIMEOUT_SEC:-60} "${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/test/warmup.py" >/dev/null 2>&1 || true
fi

