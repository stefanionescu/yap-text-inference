#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# Basic Restart Helpers
# =============================================================================
# Generic restart path for scripts/restart.sh when not using cached AWQ models.
# Handles dependency installation and standard server restart flow.

_RESTART_BASIC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../noise/logging.sh
source "${_RESTART_BASIC_DIR}/../noise/logging.sh"
# shellcheck source=./errors.sh
source "${_RESTART_BASIC_DIR}/errors.sh"
# shellcheck source=../../config/values/core.sh
source "${_RESTART_BASIC_DIR}/../../config/values/core.sh"
# shellcheck source=../../config/values/runtime.sh
source "${_RESTART_BASIC_DIR}/../../config/values/runtime.sh"
# shellcheck source=../../config/values/trt.sh
source "${_RESTART_BASIC_DIR}/../../config/values/trt.sh"
# shellcheck source=../../config/values/quantization.sh
source "${_RESTART_BASIC_DIR}/../../config/values/quantization.sh"
# shellcheck source=../../config/patterns.sh
source "${_RESTART_BASIC_DIR}/../../config/patterns.sh"

# Wipe all pip/venv dependencies and caches for a clean reinstall
# Preserves: HF cache, models, and (for chat/both) TRT repo, AWQ cache, quantized engines
# This is ONLY called when --install-deps is passed (explicit user request)
wipe_dependencies_for_reinstall() {
  local root="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

  log_info "[deps] Wiping all dependencies for clean reinstall..."

  cleanup_venvs "${root}"
  cleanup_repo_pip_cache "${root}"
  cleanup_repo_runtime_caches "${root}"
  if [ "${DEPLOY_MODE:-${CFG_DEFAULT_DEPLOY_MODE}}" != "${CFG_DEPLOY_MODE_TOOL}" ]; then
    cleanup_system_vllm_caches
    cleanup_system_trt_caches
    cleanup_system_compiler_caches
    cleanup_system_nvidia_caches
  fi
  cleanup_pip_caches

  # Remove dep hash markers (forces full reinstall)
  rm -f "${root}/.venv/.req_hash" 2>/dev/null || true
  rm -f "${root}/${CFG_TRT_QUANT_DEPS_MARKER_REL}" 2>/dev/null || true

  # Clean temp directories
  cleanup_tmp_dirs

  log_info "[deps] ✓ All dependency caches wiped. Models, HF cache, TRT repo preserved."
}

# Shared install-deps handler used by both generic and AWQ restart paths
run_install_deps_if_needed() {
  if [ "${INSTALL_DEPS:-0}" != "1" ]; then
    return 0
  fi

  log_section "[restart] Reinstalling all dependencies from scratch..."

  # Wipe all existing pip dependencies and caches for clean install
  # Preserves models, HF cache, TRT repo (if same engine)
  wipe_dependencies_for_reinstall

  # Ensure correct Python version is available (TRT needs 3.10, vLLM uses system python)
  # Tool-only only needs system python3, skip step 02
  if [ "${DEPLOY_MODE:-}" != "${CFG_DEPLOY_MODE_TOOL}" ]; then
    INFERENCE_ENGINE="${INFERENCE_ENGINE:-${CFG_DEFAULT_ENGINE}}" "${SCRIPT_DIR}/steps/02_python_env.sh" || {
      log_err "[restart] ✗ Failed to set up Python environment"
      exit 1
    }
  fi

  # Reinstall all dependencies from scratch (force mode)
  FORCE_REINSTALL=1 INFERENCE_ENGINE="${INFERENCE_ENGINE:-${CFG_DEFAULT_ENGINE}}" "${SCRIPT_DIR}/steps/03_install_deps.sh"
}

run_basic_restart() {
  local LAST_DEPLOY LAST_CHAT LAST_TOOL LAST_CHAT_QUANT
  LAST_DEPLOY="${DEPLOY_MODE:-$(read_last_config_value "DEPLOY_MODE" "${ROOT_DIR}")}"
  LAST_CHAT="${CHAT_MODEL:-$(read_last_config_value "CHAT_MODEL" "${ROOT_DIR}")}"
  LAST_TOOL="${TOOL_MODEL:-$(read_last_config_value "TOOL_MODEL" "${ROOT_DIR}")}"
  LAST_CHAT_QUANT="${CHAT_QUANTIZATION:-$(read_last_config_value "CHAT_QUANTIZATION" "${ROOT_DIR}")}"

  if [ -z "${LAST_DEPLOY}" ] || { [ -z "${LAST_CHAT}" ] && [ "${LAST_DEPLOY}" != "${CFG_DEPLOY_MODE_TOOL}" ]; } || { [ -z "${LAST_TOOL}" ] && [ "${LAST_DEPLOY}" != "${CFG_DEPLOY_MODE_CHAT}" ]; }; then
    log_err "[restart] ✗ Unable to determine previous deployment configuration. Run a full deployment first."
    exit 1
  fi

  local SHOULD_USE_GENERIC=0
  if [ -n "${CHAT_QUANTIZATION:-}" ] && [ "${CHAT_QUANTIZATION}" != "${CFG_QUANT_MODE_4BIT_BACKEND}" ]; then
    SHOULD_USE_GENERIC=1
  elif [ -n "${LAST_CHAT_QUANT}" ] && [ "${LAST_CHAT_QUANT}" != "${CFG_QUANT_MODE_4BIT_BACKEND}" ]; then
    SHOULD_USE_GENERIC=1
  fi

  # Tool-only never uses AWQ; always use the generic restart path
  if [ "${DEPLOY_MODE:-}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    SHOULD_USE_GENERIC=1
  fi

  if [ "${SHOULD_USE_GENERIC}" != "1" ]; then
    return 0
  fi

  # Non-AWQ path
  # shellcheck disable=SC2153  # DEPLOY_MODE is set by the caller via env
  local SELECTED_DEPLOY="${DEPLOY_MODE:-}"
  if [ -z "${SELECTED_DEPLOY}" ]; then
    SELECTED_DEPLOY="${DEPLOY_MODE:-${LAST_DEPLOY:-${CFG_DEFAULT_DEPLOY_MODE}}}"
  else
    case "${SELECTED_DEPLOY}" in
      "${CFG_DEPLOY_MODE_BOTH}" | "${CFG_DEPLOY_MODE_CHAT}" | "${CFG_DEPLOY_MODE_TOOL}") ;;
      *)
        SELECTED_DEPLOY="${DEPLOY_MODE:-${LAST_DEPLOY:-${CFG_DEFAULT_DEPLOY_MODE}}}"
        ;;
    esac
  fi

  if [ "${DEPLOY_MODE:-}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    unset CHAT_QUANTIZATION
  else
    # Default to "8bit" placeholder; resolved to fp8 or int8 based on GPU in quantization.sh
    export CHAT_QUANTIZATION="${CHAT_QUANTIZATION:-${LAST_CHAT_QUANT:-${CFG_QUANT_MODE_8BIT_PLACEHOLDER}}}"
  fi
  export DEPLOY_MODE="${SELECTED_DEPLOY}"

  if [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_BOTH}" ] || [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_CHAT}" ]; then
    export CHAT_MODEL="${CHAT_MODEL:-${LAST_CHAT:-}}"
  fi
  if [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_BOTH}" ] || [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    export TOOL_MODEL="${TOOL_MODEL:-${LAST_TOOL:-}}"
  fi

  if [ "${DEPLOY_MODE}" != "${CFG_DEPLOY_MODE_TOOL}" ] && [ -z "${CHAT_MODEL:-}" ]; then
    log_err "[restart] ✗ CHAT_MODEL is required for DEPLOY_MODE='${DEPLOY_MODE}'"
    [ -f "${ROOT_DIR}/${CFG_RUNTIME_SERVER_LOG_FILE}" ] && log_err "[restart] ✗ Hint: Could not parse chat model from ${CFG_RUNTIME_SERVER_LOG_FILE}"
    exit 1
  fi
  if [ "${DEPLOY_MODE}" != "${CFG_DEPLOY_MODE_CHAT}" ] && [ -z "${TOOL_MODEL:-}" ]; then
    log_err "[restart] ✗ TOOL_MODEL is required for DEPLOY_MODE='${DEPLOY_MODE}'"
    [ -f "${ROOT_DIR}/${CFG_RUNTIME_SERVER_LOG_FILE}" ] && log_err "[restart] ✗ Hint: Could not parse tool model from ${CFG_RUNTIME_SERVER_LOG_FILE}"
    exit 1
  fi

  # Validate models against allowlists before any heavy work
  if ! validate_models_early; then
    exit 1
  fi

  if [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    log_info "[restart] Quick restart: tool-only deployment"
  else
    log_info "[restart] Quick restart: reusing cached models (deploy=${DEPLOY_MODE})"
  fi

  # 1. Stop server first (before any deps/env work)
  log_section "[restart] Stopping server (preserving models and dependencies)..."
  FULL_CLEANUP=0 "${SCRIPT_DIR}/stop.sh"

  # 2. Handle --install-deps (wipe and reinstall all dependencies)
  run_install_deps_if_needed

  # 3. Load environment defaults (after deps are installed)
  source "${SCRIPT_DIR}/steps/04_env_defaults.sh"

  # 4. TRT engine: validate engine directory exists before starting server
  if [ "${INFERENCE_ENGINE:-${CFG_DEFAULT_RUNTIME_ENGINE}}" = "${CFG_ENGINE_TRT}" ] && [ "${DEPLOY_MODE}" != "${CFG_DEPLOY_MODE_TOOL}" ]; then
    if [ -z "${TRT_ENGINE_DIR:-}" ] || [ ! -d "${TRT_ENGINE_DIR:-}" ]; then
      restart_err_missing_trt_engine "${DEPLOY_MODE}"
      exit 1
    fi
    log_info "[restart] ✓ TRT engine validated"
    log_blank
  fi

  local SERVER_LOG_PATH="${ROOT_DIR}/${CFG_RUNTIME_SERVER_LOG_FILE}"
  touch "${SERVER_LOG_PATH}"
  if [ "${DEPLOY_MODE}" = "${CFG_DEPLOY_MODE_TOOL}" ]; then
    log_info "[restart] Starting server directly with existing models (tool-only deployment)..."
  else
    log_info "[restart] Starting server directly with existing models (quant=${CHAT_QUANTIZATION:-${CFG_QUANT_MODE_AUTO}})..."
  fi
  log_info "[restart] All logs: tail -f ${CFG_RUNTIME_SERVER_LOG_FILE}"
  log_info "[restart] To stop: bash scripts/stop.sh"
  log_blank

  mkdir -p "${ROOT_DIR}/${CFG_RUNTIME_RUN_DIR}"
  setsid nohup "${ROOT_DIR}/scripts/steps/05_start_server.sh" </dev/null >>"${SERVER_LOG_PATH}" 2>&1 &
  local BG_PID=$!
  echo "${BG_PID}" >"${ROOT_DIR}/${CFG_RUNTIME_DEPLOYMENT_PID_FILE}"

  log_info "[restart] ✓ Server started. Logs: tail -f ${CFG_RUNTIME_SERVER_LOG_FILE}"
  local warmup_lock="${ROOT_DIR}/${CFG_RUNTIME_WARMUP_LOCK_FILE}"
  local warmup_capture="${ROOT_DIR}/${CFG_RUNTIME_WARMUP_CAPTURE_FILE}"
  touch "${SERVER_LOG_PATH}" || true
  noise_follow_server_logs "${SERVER_LOG_PATH}" "${warmup_lock}" "${warmup_capture}"
}
