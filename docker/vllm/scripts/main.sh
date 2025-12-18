#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/logs.sh"

log_info "[main] Starting Yap Text Inference Docker Container (vLLM)"

# Usage function
usage() {
  echo "Yap Text Inference Docker Container - vLLM Engine"
  echo ""
  echo "This container is configured at build time with specific pre-quantized models."
  echo "Models are downloaded from HuggingFace on first run and cached."
  echo ""
  echo "Required Environment Variables:"
  echo "  TEXT_API_KEY                    - API key for authentication (required)"
  echo ""
  echo "Optional Environment Variables:"
  echo "  HF_TOKEN                        - HuggingFace token (for private models)"
  echo "  CHAT_GPU_FRAC                   - GPU memory fraction for chat model"
  echo "  TOOL_GPU_FRAC                   - GPU memory fraction for tool classifier"
  echo ""
  echo "Note: CHAT_MODEL and TOOL_MODEL are configured at build time."
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
log_info "[main] Setting up environment..."
source "${SCRIPT_DIR}/bootstrap.sh"

# Display final configuration
log_info "[main] "
log_info "[main] === Yap Text Inference Configuration (vLLM) ==="
log_info "[main] Deploy mode: ${DEPLOY_MODE}"
if [ "${DEPLOY_CHAT}" = "1" ]; then
  log_info "[main] Chat model: ${CHAT_MODEL}"
fi
if [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "[main] Tool model: ${TOOL_MODEL}"
fi
log_info "[main] GPU: ${DETECTED_GPU_NAME:-unknown}"
if [ -z "${TEXT_API_KEY:-}" ]; then
  log_error "[main] TEXT_API_KEY environment variable is required and must be set"
  exit 1
fi
log_info "[main] API Key: ${TEXT_API_KEY}"
log_info "[main] =========================================="
log_info "[main] "

# Start the server
log_info "[server] Starting server..."

# Robust path resolution for start script
START_SCRIPT="${SCRIPT_DIR}/start_server.sh"
if [ ! -x "${START_SCRIPT}" ]; then
  if [ -x "${SCRIPT_DIR}/common/start_server.sh" ]; then
    START_SCRIPT="${SCRIPT_DIR}/common/start_server.sh"
  else
    log_error "[server] start_server.sh not found; looked in ${SCRIPT_DIR}/start_server.sh and ${SCRIPT_DIR}/common/start_server.sh"
    ls -la "${SCRIPT_DIR}" || true
    exit 1
  fi
fi
exec "${START_SCRIPT}"

