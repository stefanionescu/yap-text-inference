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
  echo "  (At least one must be set)"
  echo ""
  echo "Optional Environment Variables:"
  echo "  DEPLOY_MODELS=both|chat|tool    - Which models to deploy (default: both)"
  echo "  CONCURRENT_MODEL_CALL=0|1       - Model calling mode (default: 1=concurrent)"
  echo "  YAP_API_KEY                     - API key for authentication (default: yap_token)"
  echo "  WARMUP_ON_START=0|1             - Run warmup on startup (default: 1)"
  echo ""
  echo "Examples:"
  echo "  # Both models (concurrent mode)"
  echo "  docker run -e AWQ_CHAT_MODEL=your-org/chat-awq -e AWQ_TOOL_MODEL=your-org/tool-awq ..."
  echo ""
  echo "  # Chat-only deployment"
  echo "  docker run -e AWQ_CHAT_MODEL=your-org/chat-awq -e DEPLOY_MODELS=chat ..."
  echo ""
  echo "  # Sequential mode (lower resource usage)"
  echo "  docker run -e CONCURRENT_MODEL_CALL=0 -e AWQ_CHAT_MODEL=... -e AWQ_TOOL_MODEL=... ..."
  echo ""
  echo "Health check: curl http://localhost:8000/healthz"
  exit 0
}

# Check if help is requested
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
  usage
fi

# Parse deployment mode from environment or arguments
if [[ $# -gt 0 ]]; then
  case "${1}" in
    chat|tool|both)
      export DEPLOY_MODELS="$1"
      shift
      ;;
    --help|-h)
      usage
      ;;
  esac
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
log_info "API Key: ${YAP_API_KEY:-yap_token}"
log_info "=========================================="
log_info ""

# Start the server
log_info "Starting server..."
exec "${SCRIPT_DIR}/start_server.sh"
