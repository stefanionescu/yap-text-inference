#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/lib/common/log.sh"
source "${SCRIPT_DIR}/lib/common/params.sh"
source "${SCRIPT_DIR}/lib/common/warmup.sh"
source "${SCRIPT_DIR}/lib/common/model_detect.sh"
source "${SCRIPT_DIR}/lib/common/model_validate.sh"
source "${SCRIPT_DIR}/lib/runtime/restart_guard.sh"
source "${SCRIPT_DIR}/lib/runtime/pipeline.sh"

log_info "Starting Yap Text Inference Server"

ensure_required_env_vars

# Determine whether quantized-model uploads should run this invocation
PUSH_QUANT=0
PARSED_ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --push-quant)
      PUSH_QUANT=1
      shift
      ;;
    --no-push-quant)
      PUSH_QUANT=0
      shift
      ;;
    --push-awq)
      log_warn "Flag --push-awq is deprecated; use --push-quant instead."
      PUSH_QUANT=1
      shift
      ;;
    --no-push-awq)
      log_warn "Flag --no-push-awq is deprecated; use --no-push-quant instead."
      PUSH_QUANT=0
      shift
      ;;
    *)
      PARSED_ARGS+=("$1")
      shift
      ;;
  esac
done
set -- "${PARSED_ARGS[@]}"
export HF_AWQ_PUSH="${PUSH_QUANT}"

# Stop any existing warmup processes before starting deployment
stop_existing_warmup_processes "${ROOT_DIR}"

# Usage function
usage() {
  echo "Usage:"
  echo "  $0 [4bit|8bit] <chat_model> <tool_model> [deploy_mode]"
  echo "  $0 [4bit|8bit] chat <chat_model>"
  echo "  $0 [4bit|8bit] tool <tool_model>"
  echo "  $0 [4bit|8bit] both <chat_model> <tool_model>"
  echo ""
  echo "Behavior:"
  echo "  • Always runs deployment in background (auto-detached)"
  echo "  • Auto-tails logs (Ctrl+C stops tail, deployment continues)"
  echo "  • Use scripts/stop.sh to stop the deployment"
  echo ""
  echo "Quantization:"
  echo "  Omit flag  → auto-detects GPTQ/AWQ/W4A16 hints; otherwise runs 8bit"
  echo "  4bit       → force low-bit chat deployment (AWQ or GPTQ depending on the model)"
  echo "  8bit       → force high-bit chat deployment:"
  echo "               • H100/L40/Ada: FP8 weights + FP8 KV cache (native FP8 support)"
  echo "               • A100/Ampere:  INT8 weights + INT8 KV cache (no FP8 support)"
  echo ""
  echo "Chat model options:"
  echo "  Float models (8bit auto): SicariusSicariiStuff/Impish_Nemo_12B"
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
  echo "Tool model options (classifier-only):"
  echo "  yapwithai/yap-longformer-screenshot-intent"
  echo "  (or any compatible transformers classifier repo/path)"
  echo ""
  echo "Required environment variables:"
  echo "  TEXT_API_KEY='secret'             - API authentication key"
  echo "  HF_TOKEN='hf_xxx'                 - Hugging Face access token"
  echo "  MAX_CONCURRENT_CONNECTIONS=<int>  - Capacity guard limit"
  echo ""
  echo "Environment options:"
  echo "  DEPLOY_MODELS=both|chat|tool  - Which models to deploy (default: both)"
  echo ""
  echo "Examples:"
  echo "  # Standard deployment (auto-background with log tailing)"
  echo "  $0 SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent"
  echo ""
  echo "  # 8B roleplay model"
  echo "  $0 SicariusSicariiStuff/Wingless_Imp_8B yapwithai/yap-longformer-screenshot-intent"
  echo ""
  echo "  # 8B highest rated uncensored model"
  echo "  $0 SicariusSicariiStuff/Impish_Mind_8B yapwithai/yap-longformer-screenshot-intent"
  echo ""
  echo "  # 4-bit AWQ for chat (tool classifier stays float)"
  echo "  $0 awq SicariusSicariiStuff/Impish_Nemo_12B yapwithai/yap-longformer-screenshot-intent"
  echo ""
  echo "  # Chat-only deployment"
  echo "  $0 chat SicariusSicariiStuff/Impish_Nemo_12B"
  echo "  DEPLOY_MODELS=chat $0 SicariusSicariiStuff/Impish_Nemo_12B"
  echo ""
  echo "  # Tool-only deployment"
  echo "  $0 tool yapwithai/yap-longformer-screenshot-intent"
  echo "  DEPLOY_MODELS=tool $0 yapwithai/yap-longformer-screenshot-intent"
  echo ""
  echo "Quantized model uploads:"
  echo "  --push-quant        Upload freshly built 4-bit exports to Hugging Face"
  echo "  --no-push-quant     Skip uploads (default)"
  exit 1
}

_resolve_4bit_backend() {
  local chat_model="$1"
  if [ -z "${chat_model}" ]; then
    echo "awq"
    return
  fi
  local classification
  classification="$(model_detect_classify_prequant "${chat_model}")"
  case "${classification}" in
    gptq) echo "gptq_marlin" ;;
    awq) echo "awq" ;;
    *) echo "awq" ;;
  esac
}

_apply_quantization_selection() {
  local forced_mode="$1"
  local chat_hint="$2"

  if [ "${DEPLOY_MODE_SELECTED}" = "tool" ]; then
    QUANT_MODE="tool-only"
    unset QUANTIZATION
    unset CHAT_QUANTIZATION
    export QUANT_MODE
    return
  fi

  local resolved_mode=""
  local resolved_backend=""

  case "${forced_mode}" in
    4bit)
      resolved_mode="4bit"
      resolved_backend="$(_resolve_4bit_backend "${CHAT_MODEL_NAME}")"
      ;;
    8bit)
      resolved_mode="8bit"
      # Backend (fp8 vs int8) is resolved later based on GPU architecture
      resolved_backend="8bit"
      ;;
    auto)
      if [ -n "${chat_hint:-}" ]; then
        resolved_mode="4bit"
        resolved_backend="${chat_hint}"
      else
        resolved_mode="8bit"
        # Backend (fp8 vs int8) is resolved later based on GPU architecture
        resolved_backend="8bit"
      fi
      ;;
    *)
      resolved_mode="8bit"
      # Backend (fp8 vs int8) is resolved later based on GPU architecture
      resolved_backend="8bit"
      ;;
  esac

  if [ "${DEPLOY_MODE_SELECTED}" != "tool" ]; then
    local prequant_kind
    prequant_kind="$(model_detect_classify_prequant "${CHAT_MODEL_NAME}")"
    case "${prequant_kind}" in
      awq)
        if [ "${resolved_backend}" != "awq" ]; then
          log_warn "Chat model '${CHAT_MODEL_NAME}' is already 4-bit (AWQ/W4A16); overriding to 4bit runtime."
          resolved_mode="4bit"
          resolved_backend="awq"
        fi
        ;;
      gptq)
        if [ "${resolved_backend}" != "gptq_marlin" ]; then
          log_warn "Chat model '${CHAT_MODEL_NAME}' is GPTQ; overriding to 4bit GPTQ runtime."
          resolved_mode="4bit"
          resolved_backend="gptq_marlin"
        fi
        ;;
    esac
  fi

  QUANT_MODE="${resolved_mode}"
  QUANTIZATION="${resolved_backend}"
  if [ "${DEPLOY_MODE_SELECTED}" != "tool" ]; then
    CHAT_QUANTIZATION="${resolved_backend}"
  fi

  export QUANT_MODE QUANTIZATION
  if [ -n "${CHAT_QUANTIZATION:-}" ]; then
    export CHAT_QUANTIZATION
  fi
}

# Parse and normalize arguments
if [ $# -lt 1 ]; then
  log_warn "Error: Not enough arguments"
  usage
fi

# Optional first token may be a quant flag
QUANT_TYPE="auto"
case "${1:-}" in
  4bit|4BIT|4Bit)
    QUANT_TYPE="4bit"
    shift
    ;;
  8bit|8BIT|8Bit)
    QUANT_TYPE="8bit"
    shift
    ;;
  awq)
    log_warn "Deprecated 'awq' flag detected; use '4bit' instead."
    QUANT_TYPE="4bit"
    shift
    ;;
  fp8)
    log_warn "Deprecated 'fp8' flag detected; use '8bit' instead."
    QUANT_TYPE="8bit"
    shift
    ;;
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
if [ "${DEPLOY_MODE_SELECTED}" != "tool" ] && [ -z "${CHAT_QUANTIZATION:-}" ]; then
  CHAT_QUANT_HINT="$(model_detect_quantization_hint "${CHAT_MODEL_NAME}")"
fi

_apply_quantization_selection "${QUANT_TYPE}" "${CHAT_QUANT_HINT}"

# Export only what is needed for selected deployment
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "chat" ]; then
  export CHAT_MODEL="${CHAT_MODEL_NAME}"
fi
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "tool" ]; then
  export TOOL_MODEL="${TOOL_MODEL_NAME}"
fi

# Early model validation - fail fast before any heavy operations
log_info "Validating model configuration..."
if ! validate_models_early; then
  log_err "Aborting deployment due to invalid model configuration"
  exit 1
fi

# Snapshot desired config for smart restart detection
DESIRED_DEPLOY_MODE="${DEPLOY_MODELS:-both}"
DESIRED_CHAT_MODEL="${CHAT_MODEL:-}"
DESIRED_TOOL_MODEL="${TOOL_MODEL:-}"
DESIRED_QUANTIZATION="${QUANTIZATION:-}"
DESIRED_CHAT_QUANT="${CHAT_QUANTIZATION:-}"
# If the server is already running, decide whether to keep caches or reset.
runtime_guard_stop_server_if_needed \
  "${SCRIPT_DIR}" \
  "${ROOT_DIR}" \
  "${DESIRED_DEPLOY_MODE}" \
  "${DESIRED_CHAT_MODEL}" \
  "${DESIRED_TOOL_MODEL}" \
  "${DESIRED_QUANTIZATION}" \
  "${DESIRED_CHAT_QUANT}"

# Display configuration
if [ "${DEPLOY_MODE_SELECTED}" = "tool" ]; then
  log_info "Configuration: quantization=tool-only (classifier runs float16)"
else
  log_info "Configuration: quantization=${QUANT_MODE:-auto} (backend=${QUANTIZATION:-<unset>}, flag=${QUANT_TYPE})"
fi
log_info "Deploy mode: ${DEPLOY_MODELS}"
if [ "${DEPLOY_MODELS}" != "tool" ]; then
  log_info "Chat model: ${CHAT_MODEL_NAME}"
fi
if [ "${DEPLOY_MODELS}" != "chat" ]; then
  log_info "Tool model: ${TOOL_MODEL_NAME}"
fi
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
export QUANTIZATION QUANT_MODE DEPLOY_MODELS CHAT_MODEL TOOL_MODEL
export CHAT_QUANTIZATION
export CHAT_MODEL_NAME TOOL_MODEL_NAME  # Also export the display names

runtime_pipeline_run_background \
  "${ROOT_DIR}" \
  "${DEPLOYMENT_CMD}" \
  "1" \
  "Starting deployment pipeline in background..."