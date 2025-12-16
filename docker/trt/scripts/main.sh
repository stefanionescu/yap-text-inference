#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "Starting Yap Text Inference Docker Container (TensorRT-LLM)"

# Usage function
usage() {
  echo "Yap Text Inference Docker Container - TensorRT-LLM Engine"
  echo ""
  echo "This container is configured at build time with specific pre-quantized models."
  echo "TRT engines are downloaded from HuggingFace on first run and cached."
  echo ""
  echo "Required Environment Variables:"
  echo "  TEXT_API_KEY                    - API key for authentication (required)"
  echo ""
  echo "Optional Environment Variables:"
  echo "  HF_TOKEN                        - HuggingFace token (for private models/engines)"
  echo "  TRT_KV_FREE_GPU_FRAC            - GPU memory fraction for KV cache (default: 0.92)"
  echo "  TRT_KV_ENABLE_BLOCK_REUSE       - Enable KV cache block reuse (default: 1)"
  echo ""
  echo "Note: CHAT_MODEL, TOOL_MODEL, and TRT_ENGINE_REPO are configured at build time."
  echo "      You don't need to specify them when running the container."
  echo ""
  echo "Example:"
  echo "  docker run --gpus all -d \\"
  echo "    -e TEXT_API_KEY=your_secret_key \\"
  echo "    -p 8000:8000 IMAGE"
  echo ""
  echo "With persistent cache (faster subsequent starts):"
  echo "  docker run --gpus all -d \\"
  echo "    -v yap-cache:/app/.hf \\"
  echo "    -v yap-engines:/opt/engines \\"
  echo "    -e TEXT_API_KEY=your_secret_key \\"
  echo "    -p 8000:8000 IMAGE"
  echo ""
  echo "Health check: curl http://localhost:8000/healthz"
  exit 0
}

# Check if help is requested
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
  usage
fi

# Validate environment and set defaults
log_info "Setting up environment..."
source "${SCRIPT_DIR}/bootstrap.sh"

# Display final configuration
log_info ""
if [ "${DEPLOY_CHAT}" = "1" ]; then
  log_info "=== Yap Text Inference Configuration (TRT-LLM) ==="
else
  log_info "=== Yap Text Inference Configuration (Tool Classifier) ==="
fi
log_info "Deploy mode: ${DEPLOY_MODELS}"
if [ "${DEPLOY_CHAT}" = "1" ]; then
  log_info "Chat model (tokenizer): ${CHAT_MODEL}"
  log_info "TRT engine repo: ${TRT_ENGINE_REPO:-<mount required>}"
fi
if [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "Tool model: ${TOOL_MODEL} (PyTorch classifier)"
fi
log_info "GPU: ${DETECTED_GPU_NAME:-unknown}"
if [ -z "${TEXT_API_KEY:-}" ]; then
  log_error "TEXT_API_KEY environment variable is required and must be set"
  exit 1
fi
log_info "API Key: ${TEXT_API_KEY}"
log_info "=========================================="
log_info ""

# Start the server
log_info "Starting server..."

# Robust path resolution for start script
START_SCRIPT="${SCRIPT_DIR}/start_server.sh"
if [ ! -x "${START_SCRIPT}" ]; then
  log_error "start_server.sh not found at ${START_SCRIPT}"
  ls -la "${SCRIPT_DIR}" || true
  exit 1
fi
exec "${START_SCRIPT}"

