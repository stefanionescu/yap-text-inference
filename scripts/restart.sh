#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/lib/common/log.sh"
source "${SCRIPT_DIR}/lib/common/params.sh"
source "${SCRIPT_DIR}/lib/restart/args.sh"
source "${SCRIPT_DIR}/lib/restart/generic.sh"
source "${SCRIPT_DIR}/lib/restart/awq.sh"
source "${SCRIPT_DIR}/lib/restart/env.sh"
source "${SCRIPT_DIR}/lib/restart/launch.sh"

log_info "Quick restart using existing models and dependencies"

ensure_required_env_vars

usage() {
  echo "Usage:"
  echo "  $0 [deploy_mode] [--install-deps]    - Restart using existing AWQ models"
  echo ""
  echo "Deploy modes:"
  echo "  both (default)  - Use both chat and tool AWQ models"
  echo "  chat            - Use only chat AWQ model"  
  echo "  tool            - Use only tool AWQ model"
  echo ""
  echo "Flags:"
  echo "  --install-deps   - Reinstall/ensure Python deps before starting (default: off)"
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
  echo "Required environment variables:"
  echo "  TEXT_API_KEY='secret'             - API key (all requests require it)"
  echo "  HF_TOKEN='hf_xxx'                 - Hugging Face access token"
  echo "  MAX_CONCURRENT_CONNECTIONS=<int>  - Capacity guard limit"
  echo ""
  echo "Optional environment variables:"
  echo "  AWQ_CHAT_MODEL=repo        - HuggingFace AWQ chat model"
  echo "  AWQ_TOOL_MODEL=repo        - HuggingFace AWQ tool model"
  echo "  CONCURRENT_MODEL_CALL=0|1  - Model calling mode (default: 1)"
  echo ""
  echo "Examples:"
  echo "  $0                         # Restart both (local or HF)"
  echo "  $0 chat                    # Restart chat-only"
  echo "  AWQ_CHAT_MODEL=yapwithai/impish-12b-awq $0 chat"
  echo "  CONCURRENT_MODEL_CALL=0 $0 # Restart sequential mode"
  echo "  $0 both --install-deps    # Force reinstall deps before start"
  exit 1
}

# Parse args using helper
if ! restart_parse_args "$@"; then
  usage
fi
case "${DEPLOY_MODE}" in both|chat|tool) : ;; *) log_warn "Invalid deploy mode '${DEPLOY_MODE}'"; usage ;; esac
export INSTALL_DEPS DEPLOY_MODE

# Generic path may start and tail the server; if not applicable, it returns
restart_generic_restart_if_needed

restart_detect_awq_models "${DEPLOY_MODE}"

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
if [ "${USING_HF_MODELS}" = "1" ]; then
  if [ ! -d "${ROOT_DIR}/.venv" ]; then
    if [ "${INSTALL_DEPS}" = "1" ]; then
      log_info "No venv found; creating and installing deps (--install-deps)"
      "${SCRIPT_DIR}/steps/02_python_env.sh"
      "${SCRIPT_DIR}/steps/03_install_deps.sh"
    else
      log_error "No virtual environment found at ${ROOT_DIR}/.venv"
      log_error "Run with --install-deps or run full deployment to set up the environment."
      exit 1
    fi
  elif [ "${INSTALL_DEPS}" = "1" ]; then
    log_info "Reinstalling/upgrading dependencies in existing venv (--install-deps)"
    "${SCRIPT_DIR}/steps/03_install_deps.sh"
  fi
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

restart_setup_env_for_awq "${DEPLOY_MODE}"

restart_apply_defaults_and_deps
restart_start_server_background
