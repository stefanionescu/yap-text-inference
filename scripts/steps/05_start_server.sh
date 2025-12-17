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
  if ! trt_assert_cuda13_driver "start_server"; then
    log_err "Aborting: CUDA 13.x required for TensorRT-LLM"
    exit 1
  fi
fi

log_info "Starting server on :8000 in background"
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
    log_warn "Server already running (PID=${OLD_PID}). Aborting start."
    exit 1
  else
    log_warn "Stale PID file found; removing ${PID_FILE}"
    rm -f "${PID_FILE}" || true
  fi
fi

# Log key env knobs
model_display="${CHAT_MODEL:-${TOOL_MODEL:-}}"
if [ "${DEPLOY_MODELS:-both}" = "tool" ]; then
  log_info "GPU=${DETECTED_GPU_NAME:-unknown} MODEL=${model_display:-<unset>} QUANT_MODE=tool-only (classifier-only)"
else
  log_info "GPU=${DETECTED_GPU_NAME:-unknown} MODEL=${model_display:-<unset>} QUANT_MODE=${QUANT_MODE:-auto} BACKEND=${QUANTIZATION:-} KV_DTYPE=${KV_DTYPE:-}"
fi
deploy_line="DEPLOY_MODELS=${DEPLOY_MODELS:-both}"
if [ "${DEPLOY_MODELS:-both}" != "tool" ]; then
  deploy_line+=" CHAT=${CHAT_MODEL:-}"
fi
if [ "${DEPLOY_MODELS:-both}" != "chat" ]; then
  deploy_line+=" TOOL=${TOOL_MODEL:-}"
fi
log_info "${deploy_line}"
log_info "TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-} VLLM_USE_V1=${VLLM_USE_V1:-} ENFORCE_EAGER=${ENFORCE_EAGER:-}"

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
  log_error "uvicorn is not installed in .venv or system."
  log_error "Run: bash scripts/steps/03_install_deps.sh"
  exit 127
fi

# Start as a new session so Ctrl+C in the calling shell won't touch it.
# Write the session leader PID so we can kill the whole tree later.
setsid "${CMD[@]}" >> "${ROOT_DIR}/server.log" 2>&1 &
SERVER_PID=$!
echo "${SERVER_PID}" > "${ROOT_DIR}/server.pid"

log_info "Server started: PID=$(cat "${ROOT_DIR}/server.pid")"
log_info "Health:  curl -s http://127.0.0.1:8000/healthz"
log_info "All logs: tail -f ${ROOT_DIR}/server.log"
log_info "Stop:    kill -TERM -$(cat "${ROOT_DIR}/server.pid")  # negative PID kills session"

WARMUP_SCRIPT="${ROOT_DIR}/scripts/warmup.sh"
if [ -x "${WARMUP_SCRIPT}" ]; then
  log_info "Running warmup validation script..."
  if ! "${WARMUP_SCRIPT}"; then
    log_warn "Warmup script detected issues (see logs/warmup.log)"
  fi
else
  log_warn "Warmup script not found at ${WARMUP_SCRIPT}"
fi

