#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Quick restart using existing AWQ models and dependencies"

usage() {
  echo "Usage:"
  echo "  $0 [deploy_mode]    - Restart using existing AWQ models"
  echo ""
  echo "Deploy modes:"
  echo "  both (default)  - Use both chat and tool AWQ models"
  echo "  chat            - Use only chat AWQ model"
  echo "  tool            - Use only tool AWQ model"
  echo ""
  echo "This script:"
  echo "  • Stops the server (light clean - preserves models/deps)"
  echo "  • Starts server directly using existing local AWQ models"
  echo "  • Skips GPU check, dependency install, and quantization"
  echo "  • Requires existing .awq/ directory with quantized models"
  echo ""
  echo "Environment variables:"
  echo "  CONCURRENT_MODEL_CALL=0|1  - Model calling mode (default: 1)"
  echo "  YAP_API_KEY                - API key (default: yap_token)"
  echo ""
  echo "Examples:"
  echo "  $0                         # Restart both models"
  echo "  $0 chat                    # Restart chat-only"
  echo "  CONCURRENT_MODEL_CALL=0 $0 # Restart sequential mode"
  exit 1
}

# Check if help is requested
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
  usage
fi

# Parse deployment mode
DEPLOY_MODE="${1:-both}"
case "${DEPLOY_MODE}" in
  both|chat|tool)
    ;;
  *)
    log_warn "Invalid deploy mode '${DEPLOY_MODE}'"
    usage
    ;;
esac

# Check if .awq directory exists
AWQ_CACHE_DIR="${ROOT_DIR}/.awq"
if [ ! -d "${AWQ_CACHE_DIR}" ]; then
  log_error "No AWQ cache directory found at ${AWQ_CACHE_DIR}"
  log_error "Run the full deployment first: bash scripts/main.sh awq <chat_model> <tool_model>"
  exit 1
fi

# Check for existing AWQ models based on deploy mode
CHAT_AWQ_DIR="${AWQ_CACHE_DIR}/chat_awq"
TOOL_AWQ_DIR="${AWQ_CACHE_DIR}/tool_awq"

if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
  if [ ! -f "${CHAT_AWQ_DIR}/awq_config.json" ] && [ ! -f "${CHAT_AWQ_DIR}/.awq_ok" ]; then
    log_error "No AWQ chat model found at ${CHAT_AWQ_DIR}"
    log_error "Run full deployment first: bash scripts/main.sh awq <chat_model> <tool_model>"
    exit 1
  fi
fi

if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
  if [ ! -f "${TOOL_AWQ_DIR}/awq_config.json" ] && [ ! -f "${TOOL_AWQ_DIR}/.awq_ok" ]; then
    log_error "No AWQ tool model found at ${TOOL_AWQ_DIR}"
    log_error "Run full deployment first: bash scripts/main.sh awq <chat_model> <tool_model>"
    exit 1
  fi
fi

# Check if venv exists
if [ ! -d "${ROOT_DIR}/.venv" ]; then
  log_error "No virtual environment found at ${ROOT_DIR}/.venv"
  log_error "Run full deployment first: bash scripts/main.sh awq <chat_model> <tool_model>"
  exit 1
fi

log_info "Found existing AWQ models and dependencies"
log_info "Deploy mode: ${DEPLOY_MODE}"
log_info "Chat AWQ: ${CHAT_AWQ_DIR}"
log_info "Tool AWQ: ${TOOL_AWQ_DIR}"

# Light stop - preserve models and dependencies
log_info "Stopping server (preserving models and dependencies)..."
NUKE_ALL=0 "${SCRIPT_DIR}/stop.sh"

# Set environment for direct server startup
export QUANTIZATION=awq
export DEPLOY_MODELS="${DEPLOY_MODE}"

# Set model paths to existing AWQ models
if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
  export CHAT_MODEL="${CHAT_AWQ_DIR}"
  export CHAT_QUANTIZATION=awq
fi

if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
  export TOOL_MODEL="${TOOL_AWQ_DIR}"
  export TOOL_QUANTIZATION=awq
fi

# Load environment defaults (for GPU detection and other settings)
log_info "Loading environment defaults..."
source "${SCRIPT_DIR}/04_env_defaults.sh"

# Create server log
SERVER_LOG="${ROOT_DIR}/server.log"
touch "${SERVER_LOG}"

log_info "Starting server directly with existing AWQ models..."
log_info "All logs: tail -f server.log"
log_info "To stop: bash scripts/stop.sh"
log_info ""

# Start server in background and tail logs
setsid nohup "${SCRIPT_DIR}/05_start_server.sh" </dev/null >> "${SERVER_LOG}" 2>&1 &
BG_PID=$!
echo "$BG_PID" > "${ROOT_DIR}/.run/deployment.pid"

log_info "Server started (PID: $BG_PID)"
log_info "Following logs (Ctrl+C detaches, server continues)..."

# Tail logs
exec tail -n +1 -F "${SERVER_LOG}"
