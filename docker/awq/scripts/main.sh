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
  echo "Required Environment Variables:"
  echo "  AWQ_CHAT_MODEL - Hugging Face repo with pre-quantized AWQ chat model"
  echo "  AWQ_TOOL_MODEL - Hugging Face repo with pre-quantized AWQ tool model"
  echo "  (Both are required; Docker always deploys both models)"
  echo ""
  echo "Optional Environment Variables:"
  echo "  YAP_API_KEY                     - API key for authentication (default: yap_token)"
  echo "  CHAT_GPU_FRAC                   - GPU memory fraction for chat model (default: 0.70)"
  echo "  TOOL_GPU_FRAC                   - GPU memory fraction for tool model (default: 0.20)"
  echo ""
  echo "Examples:"
  echo "  # Always-both deployment"
  echo "  docker run -e AWQ_CHAT_MODEL=your-org/chat-awq -e AWQ_TOOL_MODEL=your-org/tool-awq ..."
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
log_info "API Key: ${YAP_API_KEY:-yap_token}"
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
