#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/lib/common/log.sh"
source "${SCRIPT_DIR}/lib/common/params.sh"
source "${SCRIPT_DIR}/lib/common/model_guard.sh"

log_info "Starting Yap Text Inference Server"

ensure_required_env_vars

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
  echo "  Omit flag  → auto: GPTQ if chat model name contains 'GPTQ', else FP8"
  echo "  awq        → explicit 4-bit AWQ (quantizes BOTH chat and tool on load)"
  echo "             → or use pre-quantized AWQ models via AWQ_CHAT_MODEL/AWQ_TOOL_MODEL env vars"
  echo "             → Smart detection: just use 'awq' when env vars are set (no dummy params!)"
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
  echo "  AWQ_CHAT_MODEL=hf_repo        - Use pre-quantized AWQ chat model from HF (with awq flag)"
  echo "  AWQ_TOOL_MODEL=hf_repo        - Use pre-quantized AWQ tool model from HF (with awq flag)"
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
  echo "  # Use pre-quantized AWQ models from Hugging Face (no dummy params needed!)"
  echo "  AWQ_CHAT_MODEL=your-org/chat-awq AWQ_TOOL_MODEL=your-org/tool-awq $0 awq"
  echo ""
  echo "  # Chat-only with pre-quantized AWQ"
  echo "  AWQ_CHAT_MODEL=your-org/chat-awq $0 awq chat"
  echo ""
  echo "  # Tool-only with pre-quantized AWQ"
  echo "  AWQ_TOOL_MODEL=your-org/tool-awq $0 awq tool"
  echo ""
  echo "  # Chat-only deployment"
  echo "  $0 chat SicariusSicariiStuff/Impish_Nemo_12B"
  echo "  DEPLOY_MODELS=chat $0 SicariusSicariiStuff/Impish_Nemo_12B"
  echo ""
  echo "  # Tool-only deployment"
  echo "  $0 tool MadeAgents/Hammer2.1-1.5b"
  echo "  DEPLOY_MODELS=tool $0 MadeAgents/Hammer2.1-1.5b"
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

# Smart AWQ detection: if AWQ flag is set and pre-quantized models are available,
# we can auto-populate model names and skip requiring dummy parameters
USE_PREQUANT_AWQ_DETECTION=0
USE_PREQUANT_AWQ_CHAT_ONLY=0
USE_PREQUANT_AWQ_TOOL_ONLY=0

if [ "${QUANT_TYPE}" = "awq" ]; then
  if [ -n "${AWQ_CHAT_MODEL:-}" ] && [ -n "${AWQ_TOOL_MODEL:-}" ]; then
    USE_PREQUANT_AWQ_DETECTION=1
    log_info "Detected pre-quantized AWQ models (both chat & tool) - using smart parameter detection"
  elif [ -n "${AWQ_CHAT_MODEL:-}" ]; then
    USE_PREQUANT_AWQ_CHAT_ONLY=1
    log_info "Detected pre-quantized AWQ chat model - enabling smart detection for chat-only deployment"
  elif [ -n "${AWQ_TOOL_MODEL:-}" ]; then
    USE_PREQUANT_AWQ_TOOL_ONLY=1
    log_info "Detected pre-quantized AWQ tool model - enabling smart detection for tool-only deployment"
  fi
fi

# Defaults that we may fill from args
CHAT_MODEL_NAME=""
TOOL_MODEL_NAME=""
DEPLOY_MODE_SELECTED="${DEPLOY_MODELS:-}"

case "${1:-}" in
  chat)
    DEPLOY_MODE_SELECTED="chat"
    shift
    if [ $# -lt 1 ] && [ "${USE_PREQUANT_AWQ_DETECTION}" = "0" ] && [ "${USE_PREQUANT_AWQ_CHAT_ONLY}" = "0" ]; then
      log_warn "Error: chat-only mode requires <chat_model>"
      usage
    fi
    if [ "${USE_PREQUANT_AWQ_CHAT_ONLY}" = "1" ] && [ $# -eq 0 ]; then
      CHAT_MODEL_NAME="${AWQ_CHAT_MODEL}"
    else
      CHAT_MODEL_NAME="${1:-}"; [ $# -gt 0 ] && shift
    fi
    ;;
  tool)
    DEPLOY_MODE_SELECTED="tool"
    shift
    if [ $# -lt 1 ] && [ "${USE_PREQUANT_AWQ_DETECTION}" = "0" ] && [ "${USE_PREQUANT_AWQ_TOOL_ONLY}" = "0" ]; then
      log_warn "Error: tool-only mode requires <tool_model>"
      usage
    fi
    if [ "${USE_PREQUANT_AWQ_TOOL_ONLY}" = "1" ] && [ $# -eq 0 ]; then
      TOOL_MODEL_NAME="${AWQ_TOOL_MODEL}"
    else
      TOOL_MODEL_NAME="${1:-}"; [ $# -gt 0 ] && shift
    fi
    ;;
  both)
    DEPLOY_MODE_SELECTED="both"
    shift
    if [ $# -lt 2 ] && [ "${USE_PREQUANT_AWQ_DETECTION}" = "0" ]; then
      log_warn "Error: both mode requires <chat_model> <tool_model>"
      usage
    fi
    if [ "${USE_PREQUANT_AWQ_DETECTION}" = "1" ] && [ $# -eq 0 ]; then
      CHAT_MODEL_NAME="${AWQ_CHAT_MODEL}"
      TOOL_MODEL_NAME="${AWQ_TOOL_MODEL}"
    else
      CHAT_MODEL_NAME="${1:-}"; TOOL_MODEL_NAME="${2:-}"
      [ $# -gt 0 ] && shift; [ $# -gt 0 ] && shift
    fi
    ;;
  *)
    # Handle smart AWQ detection case where no model names are needed
    if [ "${USE_PREQUANT_AWQ_DETECTION}" = "1" ] && [ $# -eq 0 ]; then
      # Use pre-quantized models from environment
      CHAT_MODEL_NAME="${AWQ_CHAT_MODEL}"
      TOOL_MODEL_NAME="${AWQ_TOOL_MODEL}"
      DEPLOY_MODE_SELECTED="both"
    else
      # Backward-compatible form: <chat_model> <tool_model> [deploy_mode]
      if [ $# -lt 2 ]; then
        if [ "${USE_PREQUANT_AWQ_DETECTION}" = "1" ]; then
          log_info "Using pre-quantized AWQ models from environment variables"
          CHAT_MODEL_NAME="${AWQ_CHAT_MODEL}"
          TOOL_MODEL_NAME="${AWQ_TOOL_MODEL}"
          DEPLOY_MODE_SELECTED="both"
        else
          log_warn "Error: Must specify <chat_model> <tool_model> or use 'chat|tool' form"
          usage
        fi
      else
        CHAT_MODEL_NAME="$1"; TOOL_MODEL_NAME="$2"; shift 2
        DEPLOY_MODE_SELECTED="${1:-${DEPLOY_MODE_SELECTED:-both}}"
      fi
    fi
    ;;
esac

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

# Fail fast if selected models are not in the allowlist (unless local paths)
if [ -n "${CHAT_MODEL_NAME}" ]; then
  ensure_model_allowed "chat" "${CHAT_MODEL_NAME}"
fi
if [ -n "${TOOL_MODEL_NAME}" ]; then
  ensure_model_allowed "tool" "${TOOL_MODEL_NAME}"
fi

# Determine QUANTIZATION
case "${QUANT_TYPE}" in
  awq)
    export QUANTIZATION=awq
    if [[ "${CHAT_MODEL_NAME}" == *GPTQ* ]]; then
      log_warn "Error: For awq, provide a FLOAT chat model (not GPTQ)."
      usage
    fi
    ;;
  auto)
    if [[ "${CHAT_MODEL_NAME}" == *GPTQ* ]]; then
      export QUANTIZATION=gptq_marlin
    else
      export QUANTIZATION=fp8
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

# Create directories for runtime files  
mkdir -p "${ROOT_DIR}/.run"

# Export all environment variables for the background process
export QUANTIZATION DEPLOY_MODELS CHAT_MODEL TOOL_MODEL CONCURRENT_MODEL_CALL
export CHAT_MODEL_NAME TOOL_MODEL_NAME  # Also export the display names
export AWQ_CHAT_MODEL AWQ_TOOL_MODEL  # Pre-quantized AWQ model URLs

# Rotate log if it exists and is too large - use unified server.log for everything
SERVER_LOG="${ROOT_DIR}/server.log"
if [ -f "$SERVER_LOG" ]; then
  MAX_KEEP_BYTES=$((100 * 1024 * 1024))  # 100MB
  SIZE=$(wc -c <"$SERVER_LOG" 2>/dev/null || echo 0)
  if [ "$SIZE" -gt "$MAX_KEEP_BYTES" ]; then
    OFFSET=$((SIZE - MAX_KEEP_BYTES))
    TMP_FILE="${ROOT_DIR}/.server.log.trim"
    if tail -c "$MAX_KEEP_BYTES" "$SERVER_LOG" > "$TMP_FILE" 2>/dev/null; then
      mv "$TMP_FILE" "$SERVER_LOG" 2>/dev/null || true
      echo "[INFO] $(date -Iseconds) Trimmed server.log to latest 100MB (removed ${OFFSET} bytes)" >> "$SERVER_LOG"
    fi
  fi
fi

# Run deployment in background with proper process isolation
log_info "Starting deployment pipeline in background..."
setsid nohup bash -lc "$DEPLOYMENT_CMD" </dev/null > "$SERVER_LOG" 2>&1 &

# Store background process ID
BG_PID=$!
echo "$BG_PID" > "${ROOT_DIR}/.run/deployment.pid"

log_info "Deployment started (PID: $BG_PID)"
log_info "All logs (deployment + server): server.log" 
log_info "To stop: bash scripts/stop.sh"
echo ""
log_info "Following all logs (Ctrl+C detaches, deployment continues)..."

# Tail logs with graceful handling
touch "$SERVER_LOG" || true
exec tail -n +1 -F "$SERVER_LOG"
