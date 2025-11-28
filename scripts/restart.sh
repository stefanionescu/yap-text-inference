#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/lib/common/log.sh"
source "${SCRIPT_DIR}/lib/common/params.sh"
source "${SCRIPT_DIR}/lib/common/warmup.sh"
source "${SCRIPT_DIR}/lib/runtime/restart_guard.sh"
source "${SCRIPT_DIR}/lib/runtime/pipeline.sh"
source "${SCRIPT_DIR}/lib/restart/overrides.sh"
source "${SCRIPT_DIR}/lib/restart/args.sh"
source "${SCRIPT_DIR}/lib/restart/basic.sh"
source "${SCRIPT_DIR}/lib/restart/reconfigure.sh"
source "${SCRIPT_DIR}/lib/restart/awq.sh"
source "${SCRIPT_DIR}/lib/restart/env.sh"
source "${SCRIPT_DIR}/lib/restart/launch.sh"
source "${SCRIPT_DIR}/lib/quant/push.sh"

log_info "Restart manager ready (reuse caches or reconfigure models)"

ensure_required_env_vars

# Stop any existing warmup processes before restarting
stop_existing_warmup_processes "${ROOT_DIR}"

usage() {
  cat <<'USAGE'
Usage:
  restart.sh [deploy_mode] [--install-deps] [--keep-models]
      Quick restart that reuses existing AWQ caches (default behavior).

  restart.sh --reset-models --deploy-mode both \
             --chat-model <repo_or_path> --tool-model <repo_or_path> \
             [--chat-quant fp8|gptq|gptq_marlin|awq] \
             [--tool-quant <value>] \
             [--awq-chat-model <repo>] [--awq-tool-model <repo>] \
             [--install-deps]
      Reconfigure which models/quantization are deployed without reinstalling deps.

Deploy modes:
  both (default)  - Deploy chat + tool engines
  chat            - Deploy chat-only
  tool            - Deploy tool-only

Key flags:
  --install-deps        Reinstall dependencies inside .venv before restart
  --reset-models        Delete cached models/HF data and redeploy new models
  --keep-models         Reuse existing AWQ caches (default)
  --push-awq            Upload cached AWQ exports to Hugging Face before relaunch
  --chat-model <repo>   Chat model to deploy (required with --reset-models chat/both)
  --tool-model <repo>   Tool model to deploy (required with --reset-models tool/both)
  --chat-quant <val>    Override chat/base quantization (fp8|gptq|gptq_marlin|awq)
  --tool-quant <val>    Override tool quantization (fp8|gptq|gptq_marlin|awq)
  --awq-chat-model / --awq-tool-model
                        Use pre-quantized AWQ repos when awq is requested

This script always:
  • Stops the server
  • Preserves the repository and container
  • Keeps dependencies unless --install-deps or stop.sh removes them

Required environment variables:
  TEXT_API_KEY, HF_TOKEN (or HUGGINGFACE_HUB_TOKEN), MAX_CONCURRENT_CONNECTIONS

Examples:
  bash scripts/restart.sh                  # Reuse existing AWQ caches (both)
  bash scripts/restart.sh chat             # Chat-only AWQ restart
  bash scripts/restart.sh both --install-deps
  bash scripts/restart.sh --reset-models \
       --deploy-mode both \
       --chat-model SicariusSicariiStuff/Impish_Nemo_12B \
       --tool-model MadeAgents/Hammer2.1-3b \
       --chat-quant fp8 \
       --tool-quant awq
USAGE
  exit 1
}

# Parse args using helper
if ! restart_parse_args "$@"; then
  usage
fi
case "${DEPLOY_MODE}" in both|chat|tool) : ;; *) log_warn "Invalid deploy mode '${DEPLOY_MODE}'"; usage ;; esac
export INSTALL_DEPS DEPLOY_MODE

if [ "${RESTART_MODEL_MODE}" = "reconfigure" ]; then
  restart_reconfigure_models
  exit 0
fi

# Generic path may start and tail the server; if not applicable, it returns
restart_basic
restart_detect_awq_models "${DEPLOY_MODE}"
restart_validate_awq_push_prereqs "${DEPLOY_MODE}"

# Validate we have at least one valid source
if [ "${AWQ_SOURCES_READY:-0}" != "1" ]; then
  log_error "No AWQ models found for deploy mode '${DEPLOY_MODE}'"
  log_error ""
  log_error "Options:"
  log_error "1. Run full deployment first: bash scripts/main.sh awq <chat_model> <tool_model>"
  log_error "2. Ensure cached AWQ exports exist in ${ROOT_DIR}/.awq/"
  exit 1
fi

# Check if venv exists (only required for local models or first run)
if [ ! -d "${ROOT_DIR}/.venv" ]; then
  log_error "No virtual environment found at ${ROOT_DIR}/.venv"
  log_error "For local models: Run full deployment first: bash scripts/main.sh awq <chat_model> <tool_model>"
  log_error "For HF or other remote models: run full deployment first to cache AWQ artifacts"
  exit 1
fi

# Optional dependency refresh
if [ "${INSTALL_DEPS}" = "1" ]; then
  log_info "Reinstalling/upgrading dependencies in existing venv (--install-deps)"
  "${SCRIPT_DIR}/steps/03_install_deps.sh"
fi

# Report detected model sources
log_info "Resolved AWQ sources for restart:"
if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
  chat_origin="local cache"
  if [ "${CHAT_AWQ_SOURCE_KIND:-local}" != "local" ]; then
    chat_origin="pre-quantized repo"
  fi
  log_info "  Chat (${chat_origin}): ${CHAT_AWQ_SOURCE:-${CHAT_AWQ_DIR}}"
fi
if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
  tool_origin="local cache"
  if [ "${TOOL_AWQ_SOURCE_KIND:-local}" != "local" ]; then
    tool_origin="pre-quantized repo"
  fi
  log_info "  Tool (${tool_origin}): ${TOOL_AWQ_SOURCE:-${TOOL_AWQ_DIR}}" 
fi

# Light stop - preserve models and dependencies
log_info "Stopping server (preserving models and dependencies)..."
NUKE_ALL=0 "${SCRIPT_DIR}/stop.sh"

restart_setup_env_for_awq "${DEPLOY_MODE}"
restart_apply_defaults_and_deps
restart_push_cached_awq_models "${DEPLOY_MODE}"
restart_server_background
