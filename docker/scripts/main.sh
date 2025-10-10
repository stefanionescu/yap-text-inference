#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common/utils.sh"

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
  echo "  YAP_TEXT_API_KEY                     - API key for authentication (default: yap_token)"
  echo "  WARMUP_ON_START=0|1             - Run warmup on startup (default: 0)"
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

# Check if help is requested
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
  usage
fi

# No positional args are supported (Docker always deploys both). Help only.
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
  usage
fi

# Validate environment and set defaults
log_info "Setting up environment defaults..."
source "${SCRIPT_DIR}/common/env.sh"

# Display final configuration
log_info ""
log_info "=== AWQ Docker Deployment Configuration ==="
log_info "Deploy mode: ${DEPLOY_MODELS}"
log_info "Chat model: ${CHAT_MODEL:-none}"
log_info "Tool model: ${TOOL_MODEL:-none}"
log_info "Concurrent calls: ${CONCURRENT_MODEL_CALL}"
log_info "GPU: ${DETECTED_GPU_NAME:-unknown}"
log_info "API Key: ${YAP_TEXT_API_KEY:-yap_token}"
log_info "=========================================="
log_info ""

# Start the server
log_info "Starting server..."
exec "${SCRIPT_DIR}/start_server.sh"
