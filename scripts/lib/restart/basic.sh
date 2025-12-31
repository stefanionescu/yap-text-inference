#!/usr/bin/env bash

# Generic (non-AWQ) restart path for scripts/restart.sh
# Requires: SCRIPT_DIR, ROOT_DIR

_RESTART_BASIC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../noise/logging.sh
source "${_RESTART_BASIC_DIR}/../noise/logging.sh"

# Wipe all pip/venv dependencies and caches for a clean reinstall
# Preserves: HF cache, TRT repo, models, AWQ cache, quantized engines
# This is ONLY called when --install-deps is passed (explicit user request)
wipe_dependencies_for_reinstall() {
  local root="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  
  log_info "[deps] Wiping all dependencies for clean reinstall..."
  
  cleanup_venvs "${root}"
  cleanup_repo_pip_cache "${root}"
  cleanup_repo_runtime_caches "${root}"
  cleanup_system_vllm_caches
  cleanup_system_trt_caches
  cleanup_system_compiler_caches
  cleanup_system_nvidia_caches
  cleanup_pip_caches
  
  # Remove dep hash markers (forces full reinstall)
  rm -f "${root}/.venv/.req_hash" 2>/dev/null || true
  rm -f "${root}/.run/trt_quant_deps_installed" 2>/dev/null || true
  
  # Clean temp directories
  cleanup_tmp_dirs
  
  log_info "[deps] ✓ All dependency caches wiped. Models, HF cache, TRT repo preserved."
}

# Shared install-deps handler used by both generic and AWQ restart paths
restart_run_install_deps_if_needed() {
  if [ "${INSTALL_DEPS}" != "1" ]; then
    return 0
  fi
  
  log_section "[restart] Reinstalling all dependencies from scratch..."
  
  # Wipe all existing pip dependencies and caches for clean install
  # Preserves models, HF cache, TRT repo (if same engine)
  wipe_dependencies_for_reinstall
  
  # Ensure correct Python version is available (TRT needs 3.10, vLLM uses system python)
  INFERENCE_ENGINE="${INFERENCE_ENGINE:-trt}" "${SCRIPT_DIR}/steps/02_python_env.sh" || {
    log_err "[restart] ✗ Failed to set up Python environment"
    exit 1
  }
  
  # Reinstall all dependencies from scratch (force mode)
  FORCE_REINSTALL=1 INFERENCE_ENGINE="${INFERENCE_ENGINE:-trt}" "${SCRIPT_DIR}/steps/03_install_deps.sh"
}

restart_basic() {
  local LAST_QUANT LAST_DEPLOY LAST_CHAT LAST_TOOL LAST_CHAT_QUANT
  LAST_QUANT="${QUANTIZATION:-$(runtime_guard_read_last_config_value "QUANTIZATION" "${ROOT_DIR}")}"
  LAST_DEPLOY="${DEPLOY_MODE:-$(runtime_guard_read_last_config_value "DEPLOY_MODE" "${ROOT_DIR}")}"
  LAST_CHAT="${CHAT_MODEL:-$(runtime_guard_read_last_config_value "CHAT_MODEL" "${ROOT_DIR}")}"
  LAST_TOOL="${TOOL_MODEL:-$(runtime_guard_read_last_config_value "TOOL_MODEL" "${ROOT_DIR}")}"
  LAST_CHAT_QUANT="${CHAT_QUANTIZATION:-$(runtime_guard_read_last_config_value "CHAT_QUANTIZATION" "${ROOT_DIR}")}"

  if [ -z "${LAST_DEPLOY}" ] || { [ -z "${LAST_CHAT}" ] && [ "${LAST_DEPLOY}" != "tool" ]; } || { [ -z "${LAST_TOOL}" ] && [ "${LAST_DEPLOY}" != "chat" ]; }; then
    log_err "[restart] ✗ Unable to determine previous deployment configuration. Run a full deployment first."
    exit 1
  fi

  # Resolve quantization with proper precedence:
  # 1. Explicit CHAT_QUANTIZATION (awq, gptq, gptq_marlin) takes precedence
  # 2. QUANTIZATION from log/env as fallback
  # 3. Never override specific quant (fp8) with different specific quant (awq)
  #
  # BUG FIX: Previously this would incorrectly override fp8 with awq.
  # Now we only use CHAT_QUANTIZATION as fallback when LAST_QUANT is empty or
  # is a generic placeholder (8bit) that needs resolution.
  if [ -z "${LAST_QUANT}" ]; then
    # No quantization found in logs, use CHAT_QUANTIZATION if available
    if [ -n "${LAST_CHAT_QUANT}" ]; then
      LAST_QUANT="${LAST_CHAT_QUANT}"
    fi
  elif [ "${LAST_QUANT}" = "8bit" ]; then
    # 8bit is a placeholder - prefer specific quantization if available
    # But only use awq/gptq variants, not fp8 (which is also 8-bit precision)
    case "${LAST_CHAT_QUANT}" in
      awq|gptq|gptq_marlin)
        LAST_QUANT="${LAST_CHAT_QUANT}"
        ;;
    esac
  fi
  # For explicit values (fp8, awq, gptq, etc.) - keep as-is, don't override

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
    SELECTED_DEPLOY="${DEPLOY_MODE:-${LAST_DEPLOY:-both}}"
  fi

  if [ "${DEPLOY_MODE}" = "tool" ]; then
    unset QUANTIZATION CHAT_QUANTIZATION
  else
    # Default to "8bit" placeholder; resolved to fp8 or int8 based on GPU in quantization.sh
    export QUANTIZATION="${QUANTIZATION:-${LAST_QUANT:-8bit}}"
  fi
  export DEPLOY_MODE="${SELECTED_DEPLOY}"

  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
    export CHAT_MODEL="${CHAT_MODEL:-${LAST_CHAT:-}}"
  fi
  if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
    export TOOL_MODEL="${TOOL_MODEL:-${LAST_TOOL:-}}"
  fi

  if [ "${DEPLOY_MODE}" != "tool" ] && [ -z "${CHAT_MODEL:-}" ]; then
    log_err "[restart] ✗ CHAT_MODEL is required for DEPLOY_MODE='${DEPLOY_MODE}'"
    [ -f "${SERVER_LOG}" ] && log_err "[restart] ✗ Hint: Could not parse chat model from server.log"
    exit 1
  fi
  if [ "${DEPLOY_MODE}" != "chat" ] && [ -z "${TOOL_MODEL:-}" ]; then
    log_err "[restart] ✗ TOOL_MODEL is required for DEPLOY_MODE='${DEPLOY_MODE}'"
    [ -f "${SERVER_LOG}" ] && log_err "[restart] ✗ Hint: Could not parse tool model from server.log"
    exit 1
  fi

  # Validate models against allowlists before any heavy work
  if ! validate_models_early; then
    exit 1
  fi

  if [ "${DEPLOY_MODE}" = "tool" ]; then
    log_info "[restart] Quick restart: tool-only classifier deployment"
  else
    log_info "[restart] Quick restart: reusing cached models (deploy=${DEPLOY_MODE})"
  fi

  # 1. Stop server first (before any deps/env work)
  log_section "[restart] Stopping server (preserving models and dependencies)..."
  NUKE_ALL=0 "${SCRIPT_DIR}/stop.sh"

  # 2. Handle --install-deps (wipe and reinstall all dependencies)
  restart_run_install_deps_if_needed

  # 3. Load environment defaults (after deps are installed)
  source "${SCRIPT_DIR}/steps/04_env_defaults.sh"

  # 4. TRT engine: validate engine directory exists before starting server
  if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ] && [ "${DEPLOY_MODE}" != "tool" ]; then
    if [ -z "${TRT_ENGINE_DIR:-}" ] || [ ! -d "${TRT_ENGINE_DIR:-}" ]; then
      log_err "[restart] ✗ TRT engine directory not found or not set."
      log_err "[restart] TRT_ENGINE_DIR='${TRT_ENGINE_DIR:-<empty>}'"
      log_blank
      log_err "[restart] TensorRT-LLM requires a pre-built engine. Options:"
      log_err "[restart]   1. Build TRT engine first: bash scripts/quantization/trt_quantizer.sh <model>"
      log_err "[restart]   2. Use vLLM instead: bash scripts/restart.sh --vllm ${DEPLOY_MODE}"
      log_err "[restart]   3. Or run full deployment: bash scripts/main.sh --trt <deploy_mode> <model>"
      exit 1
    fi
    log_info "[restart] ✓ TRT engine validated"
    log_blank
  fi

  local SERVER_LOG_PATH="${ROOT_DIR}/server.log"
  touch "${SERVER_LOG_PATH}"
  if [ "${DEPLOY_MODE}" = "tool" ]; then
    log_info "[restart] Starting server directly with existing models (tool-only classifier deployment)..."
  else
    log_info "[restart] Starting server directly with existing models (quant=${QUANTIZATION})..."
  fi
  log_info "[restart] All logs: tail -f server.log"
  log_info "[restart] To stop: bash scripts/stop.sh"
  log_blank

  mkdir -p "${ROOT_DIR}/.run"
  setsid nohup "${ROOT_DIR}/scripts/steps/05_start_server.sh" </dev/null >> "${SERVER_LOG_PATH}" 2>&1 &
  local BG_PID=$!
  echo "${BG_PID}" > "${ROOT_DIR}/.run/deployment.pid"

  log_info "[restart] ✓ Server started. Logs: tail -f server.log"
  local warmup_lock="${ROOT_DIR}/.run/warmup.lock"
  local warmup_capture="${ROOT_DIR}/logs/warmup.server.log"
  touch "${SERVER_LOG_PATH}" || true
  noise_follow_server_logs "${SERVER_LOG_PATH}" "${warmup_lock}" "${warmup_capture}"
}
