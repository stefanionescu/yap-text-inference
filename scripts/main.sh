#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/lib/common/log.sh"
source "${SCRIPT_DIR}/lib/common/params.sh"
source "${SCRIPT_DIR}/lib/common/warmup.sh"
source "${SCRIPT_DIR}/lib/common/model_detect.sh"
source "${SCRIPT_DIR}/lib/runtime/restart_guard.sh"
source "${SCRIPT_DIR}/lib/runtime/pipeline.sh"

log_info "Starting Yap Text Inference Server"

ensure_required_env_vars

# Determine whether AWQ uploads should run this invocation
PUSH_AWQ=0
PARSED_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --push-awq)
      PUSH_AWQ=1
      shift
      ;;
    --no-push-awq)
      PUSH_AWQ=0
      shift
      ;;
    *)
      PARSED_ARGS+=("$1")
      shift
      ;;
  esac
done
set -- "${PARSED_ARGS[@]}"
export HF_AWQ_PUSH="${PUSH_AWQ}"

# Stop any existing warmup processes before starting deployment
stop_existing_warmup_processes "${ROOT_DIR}"

# Usage function
usage() {
  echo "Usage:"
  echo "  $0 [awq] <chat_model> <tool_model> [deploy_mode]"
  echo "  $0 [awq] chat <chat_model>"
  echo "  $0 [awq] tool <tool_model>"
  echo "  $0 [awq] both <chat_model> <tool_model>"
  echo ""
  echo "Behavior:"
  echo "  • Always runs deployment in background (auto-detached)"
  echo "  • Auto-tails logs (Ctrl+C stops tail, deployment continues)"
  echo "  • Use scripts/stop.sh to stop the deployment"
  echo ""
  echo "Quantization:"
  echo "  Omit flag  → auto-detects GPTQ/AWQ/W4A16 hints in model names; otherwise FP8"
  echo "  awq        → force 4-bit AWQ (quantizes BOTH chat and tool on load if needed)"
  echo "             → pre-quantized AWQ/W4A16 repos are detected by name automatically"
  echo ""
  echo "Chat model options:"
  echo "  Float models (FP8 auto): SicariusSicariiStuff/Impish_Nemo_12B"
  echo "                           SicariusSicariiStuff/Wingless_Imp_8B"
  echo "                           SicariusSicariiStuff/Impish_Mind_8B"
  echo "                           kyx0r/Neona-12B"
  echo "  GPTQ models (auto):      SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64"
  echo "                           SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128"
  echo "                           SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32"
  echo "  For awq (float weights): SicariusSicariiStuff/Impish_Nemo_12B"
  echo "                           SicariusSicariiStuff/Wingless_Imp_8B"
  echo "                           SicariusSicariiStuff/Impish_Mind_8B"
  echo "                           kyx0r/Neona-12B"
  echo ""
  echo "Tool model options:"
  echo "  MadeAgents/Hammer2.1-1.5b"
  echo "  MadeAgents/Hammer2.1-3b"
  echo ""
  echo "Required environment variables:"
  echo "  TEXT_API_KEY='secret'             - API authentication key"
  echo "  HF_TOKEN='hf_xxx'                 - Hugging Face access token"
  echo "  MAX_CONCURRENT_CONNECTIONS=<int>  - Capacity guard limit"
  echo ""
  echo "Environment options:"
  echo "  CONCURRENT_MODEL_CALL=1       - Enable concurrent model calls (default: 0=sequential)"
  echo "  DEPLOY_MODELS=both|chat|tool  - Which models to deploy (default: both)"
  echo ""
  echo "Examples:"
  echo "  # Sequential mode (default)"
  echo "  $0 SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # Standard deployment (auto-background with log tailing)"
  echo "  $0 SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # 8B roleplay model"
  echo "  $0 SicariusSicariiStuff/Wingless_Imp_8B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # 8B highest rated uncensored model"
  echo "  $0 SicariusSicariiStuff/Impish_Mind_8B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # Concurrent mode for lower latency"
  echo "  CONCURRENT_MODEL_CALL=1 $0 SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-3b"
  echo ""
  echo "  # GPTQ chat model (auto-detected) with concurrent mode"
  echo "  CONCURRENT_MODEL_CALL=1 $0 SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64 MadeAgents/Hammer2.1-3b"
  echo ""
  echo "  # 4-bit AWQ (quantize both chat and tool models on load)"
  echo "  $0 awq SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # Chat-only deployment"
  echo "  $0 chat SicariusSicariiStuff/Impish_Nemo_12B"
  echo "  DEPLOY_MODELS=chat $0 SicariusSicariiStuff/Impish_Nemo_12B"
  echo ""
  echo "  # Tool-only deployment"
  echo "  $0 tool MadeAgents/Hammer2.1-1.5b"
  echo "  DEPLOY_MODELS=tool $0 MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "AWQ uploads:"
  echo "  --push-awq        Explicitly upload freshly built AWQ caches to HF"
  echo "  --no-push-awq     Skip uploads (default)"
  exit 1
}

# Parse and normalize arguments
if [ $# -lt 1 ]; then
  log_warn "Error: Not enough arguments"
  usage
fi

# Optional first token may be a quant flag: 'awq' (explicit)
QUANT_TYPE="auto"
case "${1:-}" in
  awq)
    QUANT_TYPE="$1"; shift ;;
esac

# Defaults that we may fill from args
CHAT_MODEL_NAME=""
TOOL_MODEL_NAME=""
DEPLOY_MODE_SELECTED="${DEPLOY_MODELS:-}"
if [ -z "${DEPLOY_MODE_SELECTED}" ]; then
  DEPLOY_MODE_SELECTED="both"
fi
case "${DEPLOY_MODE_SELECTED}" in
  both|chat|tool) ;;
  *)
    log_warn "Invalid DEPLOY_MODELS='${DEPLOY_MODE_SELECTED}', defaulting to 'both'"
    DEPLOY_MODE_SELECTED="both"
    ;;
esac

case "${1:-}" in
  chat|tool|both)
    DEPLOY_MODE_SELECTED="${1}"
    shift
    ;;
esac

case "${DEPLOY_MODE_SELECTED}" in
  chat)
    if [ $# -lt 1 ]; then
      log_warn "Error: chat-only mode requires <chat_model>"
      usage
    fi
    CHAT_MODEL_NAME="${1}"; shift
    ;;
  tool)
    if [ $# -lt 1 ]; then
      log_warn "Error: tool-only mode requires <tool_model>"
      usage
    fi
    TOOL_MODEL_NAME="${1}"; shift
    ;;
  both)
    if [ $# -lt 2 ]; then
      log_warn "Error: both mode requires <chat_model> <tool_model>"
      usage
    fi
    CHAT_MODEL_NAME="${1}"
    TOOL_MODEL_NAME="${2}"
    shift 2
    ;;
esac

if [ "${DEPLOY_MODE_SELECTED}" != "tool" ] && [ -z "${CHAT_MODEL_NAME}" ]; then
  log_warn "Error: CHAT_MODEL is required for deploy mode '${DEPLOY_MODE_SELECTED}'"
  usage
fi
if [ "${DEPLOY_MODE_SELECTED}" != "chat" ] && [ -z "${TOOL_MODEL_NAME}" ]; then
  log_warn "Error: TOOL_MODEL is required for deploy mode '${DEPLOY_MODE_SELECTED}'"
  usage
fi

if [ $# -gt 0 ]; then
  case "${1}" in
    chat|tool|both)
      DEPLOY_MODE_SELECTED="${1}"
      shift
      ;;
  esac
fi

# Normalize and validate deploy mode selection
case "${DEPLOY_MODE_SELECTED:-both}" in
  both|chat|tool)
    export DEPLOY_MODELS="${DEPLOY_MODE_SELECTED:-both}"
    ;;
  *)
    log_warn "Invalid deploy_mode '${DEPLOY_MODE_SELECTED}', defaulting to 'both'"
    export DEPLOY_MODELS=both
    ;;
esac

# Determine per-engine quantization hints
CHAT_QUANT_HINT=""
TOOL_QUANT_HINT=""
if [ "${DEPLOY_MODE_SELECTED}" != "tool" ] && [ -z "${CHAT_QUANTIZATION:-}" ]; then
  CHAT_QUANT_HINT="$(model_detect_quantization_hint "${CHAT_MODEL_NAME}")"
fi
if [ "${DEPLOY_MODE_SELECTED}" != "chat" ] && [ -z "${TOOL_QUANTIZATION:-}" ]; then
  TOOL_QUANT_HINT="$(model_detect_quantization_hint "${TOOL_MODEL_NAME}")"
fi

# Determine QUANTIZATION
case "${QUANT_TYPE}" in
  awq)
    export QUANTIZATION=awq
    if [[ "${CHAT_MODEL_NAME}" == *GPTQ* ]]; then
      log_warn "Error: For awq, provide a FLOAT chat model (not GPTQ)."
      usage
    fi
    if [ "${DEPLOY_MODE_SELECTED}" != "tool" ]; then
      export CHAT_QUANTIZATION=awq
    fi
    if [ "${DEPLOY_MODE_SELECTED}" != "chat" ]; then
      export TOOL_QUANTIZATION=awq
    fi
    ;;
  auto)
    export QUANTIZATION=fp8
    if [ -n "${CHAT_QUANT_HINT}" ]; then
      export QUANTIZATION="${CHAT_QUANT_HINT}"
      export CHAT_QUANTIZATION="${CHAT_QUANT_HINT}"
    fi
    if [ -n "${TOOL_QUANT_HINT}" ]; then
      export TOOL_QUANTIZATION="${TOOL_QUANT_HINT}"
    elif [ -z "${TOOL_QUANTIZATION:-}" ] && [ "${DEPLOY_MODE_SELECTED}" != "chat" ] && [ "${QUANTIZATION}" != "fp8" ]; then
      # Prevent tool engine from inheriting low-bit quantization when only chat is quantized.
      export TOOL_QUANTIZATION=fp8
    fi
    ;;
esac

# Note: Model & quantization validation is centralized in Python (src/config.py).
# main.sh only passes through the selected values.

# Export only what is needed for selected deployment
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "chat" ]; then
  export CHAT_MODEL="${CHAT_MODEL_NAME}"
fi
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "tool" ]; then
  export TOOL_MODEL="${TOOL_MODEL_NAME}"
fi

# Snapshot desired config for smart restart detection
DESIRED_DEPLOY_MODE="${DEPLOY_MODELS:-both}"
DESIRED_CHAT_MODEL="${CHAT_MODEL:-}"
DESIRED_TOOL_MODEL="${TOOL_MODEL:-}"
DESIRED_QUANTIZATION="${QUANTIZATION:-}"
DESIRED_CHAT_QUANT="${CHAT_QUANTIZATION:-}"
DESIRED_TOOL_QUANT="${TOOL_QUANTIZATION:-}"

# If the server is already running, decide whether to keep caches or reset.
runtime_guard_stop_server_if_needed \
  "${SCRIPT_DIR}" \
  "${ROOT_DIR}" \
  "${DESIRED_DEPLOY_MODE}" \
  "${DESIRED_CHAT_MODEL}" \
  "${DESIRED_TOOL_MODEL}" \
  "${DESIRED_QUANTIZATION}" \
  "${DESIRED_CHAT_QUANT}" \
  "${DESIRED_TOOL_QUANT}"

# Display configuration
CONCURRENT_STATUS="concurrent (default)"
if [ "${CONCURRENT_MODEL_CALL:-1}" = "0" ]; then
  CONCURRENT_STATUS="sequential (override)"
fi

log_info "Configuration: quantization=${QUANTIZATION} (flag=${QUANT_TYPE})"
log_info "  Deploy mode: ${DEPLOY_MODELS}"
log_info "  Chat model: ${CHAT_MODEL_NAME}"
log_info "  Tool model: ${TOOL_MODEL_NAME}"
log_info "  Model calls: ${CONCURRENT_STATUS}"
log_info ""
log_info "Starting deployment in background (auto-detached)"
log_info "Ctrl+C stops log tailing only - deployment continues"
log_info "Use scripts/stop.sh to stop the deployment"

# Define the deployment pipeline command
DEPLOYMENT_CMD="
  bash '${SCRIPT_DIR}/steps/01_check_gpu.sh' && \\
  bash '${SCRIPT_DIR}/steps/02_python_env.sh' && \\
  bash '${SCRIPT_DIR}/steps/03_install_deps.sh' && \\
  source '${SCRIPT_DIR}/steps/04_env_defaults.sh' && \\
  source '${SCRIPT_DIR}/quantization/awq_quantizer.sh' && \\
  bash '${SCRIPT_DIR}/steps/05_start_server.sh' && \\
  echo '[INFO] $(date -Iseconds) Deployment process completed successfully' && \\
  echo '[INFO] $(date -Iseconds) Server is running in the background' && \\
  echo '[INFO] $(date -Iseconds) Use scripts/stop.sh to stop the server'
"

# Export all environment variables for the background process
export QUANTIZATION DEPLOY_MODELS CHAT_MODEL TOOL_MODEL CONCURRENT_MODEL_CALL
export CHAT_QUANTIZATION TOOL_QUANTIZATION
export CHAT_MODEL_NAME TOOL_MODEL_NAME  # Also export the display names

runtime_pipeline_run_background \
  "${ROOT_DIR}" \
  "${DEPLOYMENT_CMD}" \
  "1" \
  "Starting deployment pipeline in background..."