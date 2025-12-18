#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Repo root is two levels up from steps/
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${SCRIPT_DIR}/../lib/common/log.sh"
source "${SCRIPT_DIR}/../lib/runtime/restart_guard.sh"
source "${SCRIPT_DIR}/../engines/trt/detect.sh"

# Validate CUDA 13.x for TRT before starting server
if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ] || [ "${INFERENCE_ENGINE:-vllm}" = "TRT" ]; then
  if ! trt_assert_cuda13_driver "server"; then
    log_err "[cuda] CUDA 13.x required for TensorRT-LLM"
    exit 1
  fi
fi

log_info "[server] Starting server on :8000 in background"
cd "${ROOT_DIR}"
if [ -d "${ROOT_DIR}/.venv" ]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.venv/bin/activate" || true
fi

# Double-start guard and stale PID handling
PID_FILE="${ROOT_DIR}/server.pid"
if [ -f "${PID_FILE}" ]; then
  OLD_PID="$(cat "${PID_FILE}" 2>/dev/null || true)"
  if [ -n "${OLD_PID}" ] && ps -p "${OLD_PID}" >/dev/null 2>&1; then
    log_warn "[server] Server already running (PID=${OLD_PID}). Aborting start."
    exit 1
  else
    log_warn "[server] Stale PID file found; removing ${PID_FILE}"
    rm -f "${PID_FILE}" || true
  fi
fi

# Log key env knobs
log_info "[server] GPU=${DETECTED_GPU_NAME:-unknown}"

if [ "${DEPLOY_MODELS:-both}" = "both" ]; then
  log_info "[server] CHAT=${CHAT_MODEL:-}"
  log_info "[server] TOOL=${TOOL_MODEL:-}"
elif [ "${DEPLOY_MODELS:-both}" = "chat" ]; then
  log_info "[server] MODEL=${CHAT_MODEL:-}"
else
  log_info "[server] MODEL=${TOOL_MODEL:-}"
fi

if [ "${DEPLOY_MODELS:-both}" = "tool" ]; then
  log_info "[server] QUANT_MODE=tool-only (classifier-only)"
else
  log_info "[server] QUANT_MODE=${QUANT_MODE:-auto}"
  log_info "[server] BACKEND=${QUANTIZATION:-}"
  log_info "[server] KV_DTYPE=${KV_DTYPE:-}"
fi

log_info "[server] TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-} VLLM_USE_V1=${VLLM_USE_V1:-} ENFORCE_EAGER=${ENFORCE_EAGER:-}"

runtime_guard_write_snapshot "${ROOT_DIR}"

# Resolve uvicorn launcher robustly (prefer venv python -m, then venv binary, then system)
CMD_ARGS=("src.server:app" "--host" "0.0.0.0" "--port" "8000" "--workers" "1")

if [ -x "${ROOT_DIR}/.venv/bin/python" ] && "${ROOT_DIR}/.venv/bin/python" - <<'PY' >/dev/null 2>&1
import uvicorn
PY
then
  # Prefer venv python -m uvicorn to ensure correct Python interpreter
  CMD=("${ROOT_DIR}/.venv/bin/python" "-m" "uvicorn" "${CMD_ARGS[@]}")
elif [ -x "${ROOT_DIR}/.venv/bin/uvicorn" ]; then
  CMD=("${ROOT_DIR}/.venv/bin/uvicorn" "${CMD_ARGS[@]}")
elif command -v uvicorn >/dev/null 2>&1; then
  CMD=("$(command -v uvicorn)" "${CMD_ARGS[@]}")
elif command -v python3 >/dev/null 2>&1 && python3 - <<'PY' >/dev/null 2>&1
import uvicorn
PY
then
  CMD=("python3" "-m" "uvicorn" "${CMD_ARGS[@]}")
elif command -v python >/dev/null 2>&1 && python - <<'PY' >/dev/null 2>&1
import uvicorn
PY
then
  CMD=("python" "-m" "uvicorn" "${CMD_ARGS[@]}")
else
  log_error "[server] uvicorn is not installed in .venv or system."
  log_error "[server] Run: bash scripts/steps/03_install_deps.sh"
  exit 127
fi

# Start as a new session so Ctrl+C in the calling shell won't touch it.
# Write the session leader PID so we can kill the whole tree later.
setsid "${CMD[@]}" >> "${ROOT_DIR}/server.log" 2>&1 &
SERVER_PID=$!
echo "${SERVER_PID}" > "${ROOT_DIR}/server.pid"

log_info "[server] Server started: PID=$(cat "${ROOT_DIR}/server.pid")"
log_info "[server] Health:  curl -s http://127.0.0.1:8000/healthz"
log_info "[server] All logs: tail -f ${ROOT_DIR}/server.log"
log_info "[server] Stop:    kill -TERM -$(cat "${ROOT_DIR}/server.pid")  # negative PID kills session"

WARMUP_SCRIPT="${ROOT_DIR}/scripts/warmup.sh"
if [ -x "${WARMUP_SCRIPT}" ]; then
  log_info "[warmup] Running warmup validation script..."
  if ! "${WARMUP_SCRIPT}"; then
    log_warn "[warmup] Warmup script detected issues (see logs/warmup.log)"
  fi
else
  log_warn "[warmup] Warmup script not found at ${WARMUP_SCRIPT}"
fi

