#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Starting AWQ server on :8000"
cd /app

# Log key environment variables
log_info "GPU=${DETECTED_GPU_NAME:-unknown} QUANTIZATION=${QUANTIZATION:-awq}"
log_info "DEPLOY_MODELS=${DEPLOY_MODELS:-both}"
log_info "CHAT_MODEL=${CHAT_MODEL:-none} TOOL_MODEL=${TOOL_MODEL:-none}"
log_info "CONCURRENT_MODEL_CALL=${CONCURRENT_MODEL_CALL:-1}"
log_info "VLLM_USE_V1=${VLLM_USE_V1:-1} KV_DTYPE=${KV_DTYPE:-auto}"
log_info "VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-auto}"

# Start server with logging to stdout (Docker best practice)
log_info "Starting uvicorn server..."
exec uvicorn src.server:app --host 0.0.0.0 --port 8000 --workers 1
