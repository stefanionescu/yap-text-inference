#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "Starting Base server on :8000"
cd /app

# Log key environment variables
log_info "GPU=${DETECTED_GPU_NAME:-unknown} QUANTIZATION=${QUANTIZATION:-}"
log_info "DEPLOY_MODELS=${DEPLOY_MODELS:-both}"
log_info "CHAT_MODEL=${CHAT_MODEL:-none} TOOL_MODEL=${TOOL_MODEL:-none}"
log_info "CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-} TOOL_QUANTIZATION=${TOOL_QUANTIZATION:-}"
log_info "CONCURRENT_MODEL_CALL=${CONCURRENT_MODEL_CALL:-1}"
log_info "VLLM_USE_V1=${VLLM_USE_V1:-1} KV_DTYPE=${KV_DTYPE:-auto}"
log_info "VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-auto}"

# Set TOKENIZERS_PARALLELISM to avoid fork warnings
export TOKENIZERS_PARALLELISM=false

log_info "Starting uvicorn server..."
if command -v uvicorn >/dev/null 2>&1; then
  exec uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1
elif command -v python >/dev/null 2>&1 && python - <<'PY' >/dev/null 2>&1
import uvicorn
PY
then
  exec python -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1
elif command -v python3 >/dev/null 2>&1 && python3 - <<'PY' >/dev/null 2>&1
import uvicorn
PY
then
  exec python3 -m uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1
else
  echo "[ERROR] uvicorn not found in container. Ensure dependencies are installed." >&2
  exit 127
fi
