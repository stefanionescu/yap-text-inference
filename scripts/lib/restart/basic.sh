#!/usr/bin/env bash

# Generic (non-AWQ) restart path for scripts/restart.sh
# Requires: SCRIPT_DIR, ROOT_DIR

restart_basic() {
  local SERVER_LOG LAST_QUANT LAST_DEPLOY LAST_CHAT LAST_TOOL LAST_ENV_FILE
  SERVER_LOG="${ROOT_DIR}/server.log"
  LAST_QUANT=""; LAST_DEPLOY=""; LAST_CHAT=""; LAST_TOOL=""
  LAST_ENV_FILE="${ROOT_DIR}/.run/last_config.env"

  if [ -f "${SERVER_LOG}" ]; then
    LAST_QUANT=$(grep -E "Quantization: " "${SERVER_LOG}" | tail -n1 | awk -F': ' '{print $2}' | awk '{print $1}' || true)
    LAST_DEPLOY=$(grep -E "Deploy mode: " "${SERVER_LOG}" | tail -n1 | sed -E 's/.*Deploy mode: ([^ ]+).*/\1/' || true)
    LAST_CHAT=$(grep -E "Chat model: " "${SERVER_LOG}" | tail -n1 | sed -E 's/.*Chat model: *(.*)/\1/' || true)
    LAST_TOOL=$(grep -E "Tool model: " "${SERVER_LOG}" | tail -n1 | sed -E 's/.*Tool model: *(.*)/\1/' || true)
    if [ -z "${LAST_CHAT}" ] || [ "${LAST_CHAT}" = "(none)" ]; then
      LAST_CHAT=$(grep -E "CHAT=" "${SERVER_LOG}" | tail -n1 | sed -E 's/.*CHAT=([^ ]*).*/\1/' || true)
      # Fallback to MODEL= line when deploying chat-only
      if [ -z "${LAST_CHAT}" ]; then
        LAST_CHAT=$(grep -E "MODEL=" "${SERVER_LOG}" | tail -n1 | sed -E 's/.*MODEL=([^ ]*).*/\1/' || true)
      fi
    fi
    if [ -z "${LAST_TOOL}" ] || [ "${LAST_TOOL}" = "(none)" ]; then
      LAST_TOOL=$(grep -E "TOOL=" "${SERVER_LOG}" | tail -n1 | sed -E 's/.*TOOL=([^ ]*).*/\1/' || true)
    fi
  fi

  if [ -z "${LAST_QUANT}" ] && [ -f "${LAST_ENV_FILE}" ]; then
    # shellcheck disable=SC1090
    source "${LAST_ENV_FILE}" || true
    LAST_QUANT="${LAST_QUANT:-${QUANTIZATION:-}}"
    LAST_DEPLOY="${LAST_DEPLOY:-${DEPLOY_MODELS:-}}"
    LAST_CHAT="${LAST_CHAT:-${CHAT_MODEL:-}}"
    LAST_TOOL="${LAST_TOOL:-${TOOL_MODEL:-}}"
  fi


  # If the last snapshot stored explicit per-engine quantization, prefer that over
  # the generic fallback so we don't misclassify AWQ/GPTQ deployments as 8bit.
  local LAST_CHAT_QUANT="${CHAT_QUANTIZATION:-}"
  if [ -z "${LAST_QUANT}" ] || [ "${LAST_QUANT}" = "fp8" ] || [ "${LAST_QUANT}" = "8bit" ]; then
    if [ -n "${LAST_CHAT_QUANT}" ] && [ "${LAST_CHAT_QUANT}" != "fp8" ] && [ "${LAST_CHAT_QUANT}" != "8bit" ]; then
      LAST_QUANT="${LAST_CHAT_QUANT}"
    fi
  fi

  local SHOULD_USE_GENERIC=0
  if [ -n "${QUANTIZATION:-}" ] && [ "${QUANTIZATION}" != "awq" ]; then
    SHOULD_USE_GENERIC=1
  elif [ -n "${LAST_QUANT}" ] && [ "${LAST_QUANT}" != "awq" ]; then
    SHOULD_USE_GENERIC=1
  fi

  if [ "${SHOULD_USE_GENERIC}" != "1" ]; then
    return 0
  fi

  # Non-AWQ path
  # shellcheck disable=SC2153  # DEPLOY_MODE is set by the caller via env
  local SELECTED_DEPLOY="${DEPLOY_MODE}"
  if [ -z "${SELECTED_DEPLOY}" ] || ! [[ "${SELECTED_DEPLOY}" =~ ^(both|chat|tool)$ ]]; then
    SELECTED_DEPLOY="${DEPLOY_MODELS:-${LAST_DEPLOY:-both}}"
  fi

  if [ "${DEPLOY_MODELS}" = "tool" ]; then
    unset QUANTIZATION CHAT_QUANTIZATION
  else
    # Default to "8bit" placeholder; resolved to fp8 or int8 based on GPU in quantization.sh
    export QUANTIZATION="${QUANTIZATION:-${LAST_QUANT:-8bit}}"
  fi
  export DEPLOY_MODELS="${SELECTED_DEPLOY}"

  if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "chat" ]; then
    export CHAT_MODEL="${CHAT_MODEL:-${LAST_CHAT:-}}"
  fi
  if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "tool" ]; then
    export TOOL_MODEL="${TOOL_MODEL:-${LAST_TOOL:-}}"
  fi

  if [ "${DEPLOY_MODELS}" != "tool" ] && [ -z "${CHAT_MODEL:-}" ]; then
    log_error "[restart] CHAT_MODEL is required for DEPLOY_MODELS='${DEPLOY_MODELS}'"
    [ -f "${SERVER_LOG}" ] && log_error "[restart] Hint: Could not parse chat model from server.log"
    exit 1
  fi
  if [ "${DEPLOY_MODELS}" != "chat" ] && [ -z "${TOOL_MODEL:-}" ]; then
    log_error "[restart] TOOL_MODEL is required for DEPLOY_MODELS='${DEPLOY_MODELS}'"
    [ -f "${SERVER_LOG}" ] && log_error "[restart] Hint: Could not parse tool model from server.log"
    exit 1
  fi

  local display_quant="${QUANTIZATION:-tool-only}"
  if [ "${DEPLOY_MODELS}" != "tool" ]; then
    display_quant="${QUANTIZATION:-<unset>}"
  fi
  log_info "[restart] Quick restart: reusing cached ${display_quant} models (deploy=${DEPLOY_MODELS})"

  log_info "[restart] Stopping server (preserving models and dependencies)..."
  NUKE_ALL=0 "${SCRIPT_DIR}/stop.sh"

  log_info "[restart] Loading environment defaults..."
  source "${SCRIPT_DIR}/steps/04_env_defaults.sh"

  if [ "${INSTALL_DEPS}" = "1" ]; then
    log_info "[restart] Installing dependencies as requested (--install-deps)"
    "${SCRIPT_DIR}/steps/02_python_env.sh"
    "${SCRIPT_DIR}/steps/03_install_deps.sh"
  else
    log_info "[restart] Skipping dependency installation (default)"
  fi

  local SERVER_LOG_PATH="${ROOT_DIR}/server.log"
  touch "${SERVER_LOG_PATH}"
  if [ "${DEPLOY_MODELS}" = "tool" ]; then
    log_info "[restart] Starting server directly with existing models (tool-only classifier deployment)..."
  else
    log_info "[restart] Starting server directly with existing models (quant=${QUANTIZATION})..."
  fi
  log_info "[restart] All logs: tail -f server.log"
  log_info "[restart] To stop: bash scripts/stop.sh"
  log_info "[restart] "

  mkdir -p "${ROOT_DIR}/.run"
  setsid nohup "${ROOT_DIR}/scripts/steps/05_start_server.sh" </dev/null >> "${SERVER_LOG_PATH}" 2>&1 &
  local BG_PID=$!
  echo "${BG_PID}" > "${ROOT_DIR}/.run/deployment.pid"

  log_info "[restart] Server started (PID: ${BG_PID})"
  log_info "[restart] Following logs (Ctrl+C detaches, server continues)..."
  exec tail -n +1 -F "${SERVER_LOG_PATH}"
}
