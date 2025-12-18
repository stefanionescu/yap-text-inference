#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "[vllm] Starting vLLM server on :8000"
cd /app

# Log key environment variables
log_info "[vllm] GPU=${DETECTED_GPU_NAME:-unknown} QUANTIZATION=${QUANTIZATION:-awq}"
log_info "[vllm] DEPLOY_MODE=${DEPLOY_MODE:-both}"
if [ "${DEPLOY_CHAT:-0}" = "1" ]; then
  log_info "[vllm] CHAT_MODEL=${CHAT_MODEL:-none}"
fi
if [ "${DEPLOY_TOOL:-0}" = "1" ]; then
  log_info "[vllm] TOOL_MODEL=${TOOL_MODEL:-none}"
fi
log_info "[vllm] VLLM_USE_V1=${VLLM_USE_V1:-1} KV_DTYPE=${KV_DTYPE:-auto}"
log_info "[vllm] VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-auto}"

# Resolve uvicorn command
if command -v uvicorn >/dev/null 2>&1; then
  UVICORN_CMD=(uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
elif command -v python >/dev/null 2>&1 && python -c "import uvicorn" 2>/dev/null; then
  UVICORN_CMD=(python -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
elif command -v python3 >/dev/null 2>&1 && python3 -c "import uvicorn" 2>/dev/null; then
  UVICORN_CMD=(python3 -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1)
else
  echo "[vllm] uvicorn not found in container. Ensure dependencies are installed." >&2
  exit 127
fi

log_info "[vllm] Starting uvicorn server..."
"${UVICORN_CMD[@]}" &
SERVER_PID=$!

# Run warmup in background
log_info "[vllm] Running warmup validation in background..."
"${SCRIPT_DIR}/warmup.sh" &

# Wait on server (container stays alive)
wait "${SERVER_PID}"

