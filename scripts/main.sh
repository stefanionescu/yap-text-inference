#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/utils.sh"

log_info "Starting Yap Text Inference Server"

# Usage function
usage() {
  echo "Usage:"
  echo "  $0 [--background] [awq] <chat_model> <tool_model> [deploy_mode]"
  echo "  $0 [--background] [awq] chat <chat_model>"
  echo "  $0 [--background] [awq] tool <tool_model>"
  echo "  $0 [--background] [awq] both <chat_model> <tool_model>"
  echo ""
  echo "Options:"
  echo "  --background   → Run deployment in background with log tailing (Ctrl+C exits tail only)"
  echo ""
  echo "Quantization:"
  echo "  Omit flag  → auto: GPTQ if chat model name contains 'GPTQ', else FP8"
  echo "  awq        → explicit 4-bit AWQ (quantizes BOTH chat and tool on load)"
  echo ""
  echo "Chat model options:"
  echo "  Float models (FP8 auto): SicariusSicariiStuff/Impish_Nemo_12B"
  echo "                           SicariusSicariiStuff/Wingless_Imp_8B"
  echo "                           SicariusSicariiStuff/Impish_Mind_8B"
  echo "                           kyx0r/Neona-12B"
  echo "                           w4r10ck/SOLAR-10.7B-Instruct-v1.0-uncensored"
  echo "  GPTQ models (auto):      SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-64"
  echo "                           SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128"
  echo "                           SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-32"
  echo "  For awq (float weights): SicariusSicariiStuff/Impish_Nemo_12B"
  echo "                           SicariusSicariiStuff/Wingless_Imp_8B"
  echo "                           SicariusSicariiStuff/Impish_Mind_8B"
  echo "                           kyx0r/Neona-12B"
  echo "                           w4r10ck/SOLAR-10.7B-Instruct-v1.0-uncensored"
  echo ""
  echo "Tool model options:"
  echo "  MadeAgents/Hammer2.1-1.5b"
  echo "  MadeAgents/Hammer2.1-3b"
  echo ""
  echo "Environment options:"
  echo "  CONCURRENT_MODEL_CALL=1       - Enable concurrent model calls (default: 0=sequential)"
  echo "  DEPLOY_MODELS=both|chat|tool  - Which models to deploy (default: both)"
  echo ""
  echo "Examples:"
  echo "  # Sequential mode (default)"
  echo "  $0 SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # Background deployment with log tailing (recommended)"
  echo "  $0 --background SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
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
  echo "  # Background AWQ deployment"
  echo "  $0 --background awq SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # Chat-only deployment"
  echo "  $0 chat SicariusSicariiStuff/Impish_Nemo_12B"
  echo "  DEPLOY_MODELS=chat $0 SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
  echo ""
  echo "  # Tool-only deployment"
  echo "  $0 tool MadeAgents/Hammer2.1-1.5b"
  echo "  DEPLOY_MODELS=tool $0 SicariusSicariiStuff/Impish_Nemo_12B MadeAgents/Hammer2.1-1.5b"
  exit 1
}

# Parse and normalize arguments
# Check for --background flag first
BACKGROUND_FLAG=""
if [ "${1:-}" = "--background" ]; then
  BACKGROUND_FLAG="--background"
  shift
fi

if [ $# -lt 1 ]; then
  log_warn "Error: Not enough arguments"
  usage
fi

# Optional first token may be a quant flag: 'awq' (explicit), or deprecated '8bit'/'4bit'
QUANT_TYPE="auto"
case "${1:-}" in
  awq|8bit|4bit)
    QUANT_TYPE="$1"; shift ;;
esac

# Defaults that we may fill from args
CHAT_MODEL_NAME=""
TOOL_MODEL_NAME=""
DEPLOY_MODE_SELECTED="${DEPLOY_MODELS:-}"

case "${1:-}" in
  chat)
    DEPLOY_MODE_SELECTED="chat"
    shift
    if [ $# -lt 1 ]; then
      log_warn "Error: chat-only mode requires <chat_model>"
      usage
    fi
    CHAT_MODEL_NAME="$1"; shift
    ;;
  tool)
    DEPLOY_MODE_SELECTED="tool"
    shift
    if [ $# -lt 1 ]; then
      log_warn "Error: tool-only mode requires <tool_model>"
      usage
    fi
    TOOL_MODEL_NAME="$1"; shift
    ;;
  both)
    DEPLOY_MODE_SELECTED="both"
    shift
    if [ $# -lt 2 ]; then
      log_warn "Error: both mode requires <chat_model> <tool_model>"
      usage
    fi
    CHAT_MODEL_NAME="$1"; TOOL_MODEL_NAME="$2"; shift 2
    ;;
  *)
    # Backward-compatible form: <chat_model> <tool_model> [deploy_mode]
    if [ $# -lt 2 ]; then
      log_warn "Error: Must specify <chat_model> <tool_model> or use 'chat|tool' form"
      usage
    fi
    CHAT_MODEL_NAME="$1"; TOOL_MODEL_NAME="$2"; shift 2
    DEPLOY_MODE_SELECTED="${1:-${DEPLOY_MODE_SELECTED:-both}}"
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

# Determine QUANTIZATION
case "${QUANT_TYPE}" in
  awq)
    export QUANTIZATION=awq
    if [[ "${CHAT_MODEL_NAME}" == *GPTQ* ]]; then
      log_warn "Error: For awq, provide a FLOAT chat model (not GPTQ)."
      usage
    fi
    ;;
  8bit)
    log_warn "Deprecated flag '8bit'. Omit the flag to auto-detect FP8/GPTQ; keeping compatibility."
    export QUANTIZATION=fp8
    ;;
  4bit)
    log_warn "Deprecated flag '4bit'. Omit the flag; GPTQ will be auto-detected."
    export QUANTIZATION=gptq_marlin
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

# Function to run the deployment process
run_deployment() {
  bash "${SCRIPT_DIR}/01_check_gpu.sh"
  bash "${SCRIPT_DIR}/02_python_env.sh"
  bash "${SCRIPT_DIR}/03_install_deps.sh"
  source "${SCRIPT_DIR}/04_env_defaults.sh"
  bash "${SCRIPT_DIR}/05_start_server.sh"
  
  log_info "Deployment process completed successfully"
  log_info "Server is running in the background"
  log_info "Use 'tail -f ${ROOT_DIR}/server.log' to follow server logs"
  log_info "Use scripts/stop.sh to stop the server"
}

# Function to handle log rotation for deployment logs
rotate_deployment_log() {
  local log_file="${ROOT_DIR}/deployment.log"
  if [ -f "$log_file" ]; then
    local max_keep_bytes=$((100 * 1024 * 1024))  # 100MB
    local sz=$(wc -c <"$log_file" 2>/dev/null || echo 0)
    if [ "$sz" -gt "$max_keep_bytes" ]; then
      local offset=$((sz - max_keep_bytes))
      local tmp_file="${ROOT_DIR}/.deployment.log.trim"
      if tail -c "$max_keep_bytes" "$log_file" > "$tmp_file" 2>/dev/null; then
        mv "$tmp_file" "$log_file" 2>/dev/null || true
        echo "[INFO] $(timestamp) Trimmed deployment.log to latest 100MB (removed ${offset} bytes)" >> "$log_file"
      fi
    fi
  fi
}

# Check if we should run in background
if [ -n "${BACKGROUND_FLAG}" ] || [ "${BACKGROUND_DEPLOY:-0}" = "1" ]; then
  
  # Rotate log before starting
  rotate_deployment_log
  
  # Run deployment in background with logging
  {
    log_info "Starting background deployment process"
    log_info "Follow progress with: tail -f ${ROOT_DIR}/deployment.log"
    log_info "Stop deployment with: pkill -f 'bash.*main.sh' (if still running)"
    echo ""
    
    # Re-run this script without background flag in a new session
    setsid bash "$0" "$@" 2>&1
  } >> "${ROOT_DIR}/deployment.log" &
  
  DEPLOY_PID=$!
  echo "$DEPLOY_PID" > "${ROOT_DIR}/deployment.pid"
  
  echo "[INFO] $(timestamp) Deployment started in background (PID=${DEPLOY_PID})"
  echo "[INFO] $(timestamp) Follow progress with: tail -f ${ROOT_DIR}/deployment.log"
  echo "[INFO] $(timestamp) Stop with Ctrl+C (only stops tail, deployment continues)"
  echo ""
  
  # Start tailing the log file
  sleep 1  # Give a moment for the log to be created
  tail -f "${ROOT_DIR}/deployment.log" 2>/dev/null || {
    echo "[WARN] $(timestamp) deployment.log not yet available, waiting..."
    sleep 2
    tail -f "${ROOT_DIR}/deployment.log" 2>/dev/null || true
  }
else
  # Run normally (for background execution or direct execution)
  run_deployment
fi


