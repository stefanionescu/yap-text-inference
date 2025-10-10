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
  echo "AWQ Model Sources (auto-detected):"
  echo "  • Local models: Uses .awq/ directory (created by full deployment)"
  echo "  • HF models: Uses AWQ_CHAT_MODEL/AWQ_TOOL_MODEL environment variables"
  echo ""
  echo "This script:"
  echo "  • Stops the server (light clean - preserves models/deps)"
  echo "  • Starts server directly using existing AWQ models"
  echo "  • Skips GPU check, dependency install, and quantization"
  echo "  • Works with both local and HuggingFace AWQ models"
  echo ""
  echo "Environment variables:"
  echo "  AWQ_CHAT_MODEL=repo        - HuggingFace AWQ chat model"
  echo "  AWQ_TOOL_MODEL=repo        - HuggingFace AWQ tool model"
  echo "  CONCURRENT_MODEL_CALL=0|1  - Model calling mode (default: 1)"
  echo "  YAP_API_KEY                - API key (default: yap_token)"
  echo ""
  echo "Examples:"
  echo "  $0                         # Restart both (local or HF)"
  echo "  $0 chat                    # Restart chat-only"
  echo "  AWQ_CHAT_MODEL=yapwithai/impish-12b-awq $0 chat"
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

# Detect AWQ model sources (local or HuggingFace)
AWQ_CACHE_DIR="${ROOT_DIR}/.awq"
CHAT_AWQ_DIR="${AWQ_CACHE_DIR}/chat_awq"
TOOL_AWQ_DIR="${AWQ_CACHE_DIR}/tool_awq"

USING_LOCAL_MODELS=0
USING_HF_MODELS=0

# Check for local AWQ models
if [ -d "${AWQ_CACHE_DIR}" ]; then
  LOCAL_CHAT_OK=0
  LOCAL_TOOL_OK=0
  
  if [ -f "${CHAT_AWQ_DIR}/awq_config.json" ] || [ -f "${CHAT_AWQ_DIR}/.awq_ok" ]; then
    LOCAL_CHAT_OK=1
  fi
  
  if [ -f "${TOOL_AWQ_DIR}/awq_config.json" ] || [ -f "${TOOL_AWQ_DIR}/.awq_ok" ]; then
    LOCAL_TOOL_OK=1
  fi
  
  # Check if we have the required local models for the deploy mode
  case "${DEPLOY_MODE}" in
    both)
      if [ "${LOCAL_CHAT_OK}" = "1" ] && [ "${LOCAL_TOOL_OK}" = "1" ]; then
        USING_LOCAL_MODELS=1
      fi
      ;;
    chat)
      if [ "${LOCAL_CHAT_OK}" = "1" ]; then
        USING_LOCAL_MODELS=1
      fi
      ;;
    tool)
      if [ "${LOCAL_TOOL_OK}" = "1" ]; then
        USING_LOCAL_MODELS=1
      fi
      ;;
  esac
fi

# Check for HuggingFace AWQ models
HF_CHAT_OK=0
HF_TOOL_OK=0

if [ -n "${AWQ_CHAT_MODEL:-}" ]; then
  HF_CHAT_OK=1
fi

if [ -n "${AWQ_TOOL_MODEL:-}" ]; then
  HF_TOOL_OK=1
fi

# Check if we have the required HF models for the deploy mode  
case "${DEPLOY_MODE}" in
  both)
    if [ "${HF_CHAT_OK}" = "1" ] && [ "${HF_TOOL_OK}" = "1" ]; then
      USING_HF_MODELS=1
    fi
    ;;
  chat)
    if [ "${HF_CHAT_OK}" = "1" ]; then
      USING_HF_MODELS=1
    fi
    ;;
  tool)
    if [ "${HF_TOOL_OK}" = "1" ]; then
      USING_HF_MODELS=1
    fi
    ;;
esac

# Validate we have at least one valid source
if [ "${USING_LOCAL_MODELS}" = "0" ] && [ "${USING_HF_MODELS}" = "0" ]; then
  log_error "No AWQ models found for deploy mode '${DEPLOY_MODE}'"
  log_error ""
  log_error "Options:"
  log_error "1. Run full deployment first: bash scripts/main.sh awq <chat_model> <tool_model>"
  log_error "2. Set HuggingFace AWQ models:"
  log_error "   AWQ_CHAT_MODEL=yapwithai/impish-12b-awq AWQ_TOOL_MODEL=yapwithai/hammer-2.1-3b-awq $0 ${DEPLOY_MODE}"
  exit 1
fi

# Check if venv exists (only required for local models or first run)
if [ ! -d "${ROOT_DIR}/.venv" ] && [ "${USING_HF_MODELS}" = "0" ]; then
  log_error "No virtual environment found at ${ROOT_DIR}/.venv"
  log_error "For local models: Run full deployment first: bash scripts/main.sh awq <chat_model> <tool_model>"
  log_error "For HF models: Set AWQ_CHAT_MODEL/AWQ_TOOL_MODEL and run full deployment first"
  exit 1
fi

# For HF models, create venv if it doesn't exist
if [ "${USING_HF_MODELS}" = "1" ] && [ ! -d "${ROOT_DIR}/.venv" ]; then
  log_info "HuggingFace AWQ models detected - setting up minimal environment"
  "${SCRIPT_DIR}/02_python_env.sh"
  "${SCRIPT_DIR}/03_install_deps.sh"
fi

# Report detected model sources
if [ "${USING_LOCAL_MODELS}" = "1" ]; then
  log_info "Using LOCAL AWQ models:"
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
    log_info "  Chat: ${CHAT_AWQ_DIR}"
  fi
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
    log_info "  Tool: ${TOOL_AWQ_DIR}" 
  fi
elif [ "${USING_HF_MODELS}" = "1" ]; then
  log_info "Using HUGGINGFACE AWQ models:"
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
    log_info "  Chat: ${AWQ_CHAT_MODEL}"
  fi
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
    log_info "  Tool: ${AWQ_TOOL_MODEL}"
  fi
fi

# Light stop - preserve models and dependencies
log_info "Stopping server (preserving models and dependencies)..."
NUKE_ALL=0 "${SCRIPT_DIR}/stop.sh"

# Set environment for direct server startup
export QUANTIZATION=awq
export DEPLOY_MODELS="${DEPLOY_MODE}"

# Set model paths based on detected source
if [ "${USING_LOCAL_MODELS}" = "1" ]; then
  # Use local AWQ models
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
    export CHAT_MODEL="${CHAT_AWQ_DIR}"
    export CHAT_QUANTIZATION=awq
  fi
  
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
    export TOOL_MODEL="${TOOL_AWQ_DIR}" 
    export TOOL_QUANTIZATION=awq
  fi
elif [ "${USING_HF_MODELS}" = "1" ]; then
  # Use HuggingFace AWQ models 
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
    export CHAT_MODEL="${AWQ_CHAT_MODEL}"
    export CHAT_QUANTIZATION=awq
  fi
  
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
    export TOOL_MODEL="${AWQ_TOOL_MODEL}"
    export TOOL_QUANTIZATION=awq
  fi
fi

# Load environment defaults (for GPU detection and other settings)
log_info "Loading environment defaults..."
source "${SCRIPT_DIR}/04_env.sh"

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
