#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "Starting Yap Text Inference Docker Container (AWQ Mode)"

# Usage function
usage() {
  echo "Yap Text Inference Docker Container - AWQ Pre-quantized Models"
  echo ""
  echo "This container only supports pre-quantized AWQ models from Hugging Face."
  echo ""
  echo "Required Environment Variables (based on DEPLOY_MODELS):"
  echo "  DEPLOY_MODELS=both|chat|tool  (default: both)"
  echo "  If DEPLOY_MODELS=chat  -> AWQ_CHAT_MODEL required"
  echo "  If DEPLOY_MODELS=tool  -> AWQ_TOOL_MODEL required"
  echo "  If DEPLOY_MODELS=both  -> AWQ_CHAT_MODEL and AWQ_TOOL_MODEL required"
  echo ""
  echo "Optional Environment Variables:"
  echo "  TEXT_API_KEY                     - API key for authentication (required, no default)"
  echo "  CHAT_GPU_FRAC                   - GPU memory fraction for chat model (default: 0.70)"
  echo "  TOOL_GPU_FRAC                   - GPU memory fraction for tool model (default: 0.20)"
  echo ""
  echo "Examples:"
  echo "  # Both models"
  echo "  docker run --gpus all -d \\
  -e DEPLOY_MODELS=both \\
  -e AWQ_CHAT_MODEL=your-org/chat-awq \\
  -e AWQ_TOOL_MODEL=your-org/tool-awq IMAGE"
  echo ""
  echo "  # Chat only"
  echo "  docker run --gpus all -d \\
  -e DEPLOY_MODELS=chat \\
  -e AWQ_CHAT_MODEL=your-org/chat-awq IMAGE"
  echo ""
  echo "  # Tool only"
  echo "  docker run --gpus all -d \\
  -e DEPLOY_MODELS=tool \\
  -e AWQ_TOOL_MODEL=your-org/tool-awq IMAGE"
  echo ""
  echo "Health check: curl http://localhost:8000/healthz"
  exit 0
}

# Check if help is requested (no positional args supported)
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
  usage
fi

# Validate environment and set defaults
log_info "Setting up environment defaults..."
source "${SCRIPT_DIR}/bootstrap.sh"

# Display final configuration
log_info ""
log_info "=== AWQ Docker Deployment Configuration ==="
log_info "Deploy mode: ${DEPLOY_MODELS}"
log_info "Chat model: ${CHAT_MODEL:-none}"
log_info "Tool model: ${TOOL_MODEL:-none}"
log_info "Concurrent calls: ${CONCURRENT_MODEL_CALL}"
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
  if [ -x "${SCRIPT_DIR}/common/start_server.sh" ]; then
    START_SCRIPT="${SCRIPT_DIR}/common/start_server.sh"
  else
    log_error "start_server.sh not found; looked in ${SCRIPT_DIR}/start_server.sh and ${SCRIPT_DIR}/common/start_server.sh"
    ls -la "${SCRIPT_DIR}" || true
    exit 1
  fi
fi
exec "${START_SCRIPT}"
