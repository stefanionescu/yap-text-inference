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
source "${SCRIPT_DIR}/lib/env/restart.sh"
source "${SCRIPT_DIR}/lib/restart/launch.sh"
source "${SCRIPT_DIR}/engines/vllm/push.sh"
source "${SCRIPT_DIR}/engines/trt/detect.sh"

log_info "[restart] Restart manager ready (reuse caches or reconfigure models)"

ensure_required_env_vars

# Stop any existing warmup processes before restarting
stop_existing_warmup_processes "${ROOT_DIR}"

usage() {
  cat <<'USAGE'
Usage:
  restart.sh [deploy_mode] [--trt|--vllm] [--install-deps] [--keep-models]
      Quick restart that reuses existing quantized caches (default behavior).

  restart.sh --reset-models --deploy-mode both \
             --chat-model <repo_or_path> --tool-model <repo_or_path> \
             [--trt|--vllm] [--chat-quant 4bit|8bit|fp8|gptq|gptq_marlin|awq] \
             [--install-deps]
      Reconfigure which models/quantization are deployed without reinstalling deps.

Inference Engines:
  --trt           Use TensorRT-LLM engine (default)
  --vllm          Use vLLM engine
  --engine=X      Explicit engine selection (trt or vllm)

  NOTE: Switching engines (trt <-> vllm) triggers FULL environment wipe:
        all HF caches, pip deps, quantized models, and engine artifacts.

Deploy modes:
  both (default)  - Deploy chat + tool engines
  chat            - Deploy chat-only
  tool            - Deploy tool-only

Key flags:
  --install-deps        Reinstall dependencies inside .venv before restart
  --reset-models        Delete cached models/HF data and redeploy new models
  --keep-models         Reuse existing quantized caches (default)
  --push-quant          Upload cached 4-bit exports to Hugging Face before relaunch
  --chat-model <repo>   Chat model to deploy (required with --reset-models chat/both)
  --tool-model <repo>   Tool model to deploy (required with --reset-models tool/both)
  --chat-quant <val>    Override chat/base quantization (4bit|8bit|fp8|gptq|gptq_marlin|awq).
                        `4bit` aliases AWQ. `8bit` uses FP8 (L40S/H100) or INT8-SQ (A100).
                        Pre-quantized repos are detected automatically.

This script always:
  • Stops the server
  • Preserves the repository and container
  • Keeps dependencies unless --install-deps or stop.sh removes them

Required environment variables:
  TEXT_API_KEY, HF_TOKEN (or HUGGINGFACE_HUB_TOKEN), MAX_CONCURRENT_CONNECTIONS

Examples:
  bash scripts/restart.sh                  # TRT engine with existing caches
  bash scripts/restart.sh --vllm           # Switch to vLLM (triggers full wipe)
  bash scripts/restart.sh chat             # Chat-only restart
  bash scripts/restart.sh both --install-deps
  bash scripts/restart.sh --reset-models \
       --deploy-mode both \
       --chat-model SicariusSicariiStuff/Impish_Nemo_12B \
       --tool-model yapwithai/yap-longformer-screenshot-intent \
       --chat-quant 8bit
USAGE
  exit 1
}

# Parse args using helper
if ! restart_parse_args "$@"; then
  usage
fi
case "${DEPLOY_MODE}" in both|chat|tool) : ;; *) log_warn "[restart] Invalid deploy mode '${DEPLOY_MODE}'"; usage ;; esac
export INSTALL_DEPS DEPLOY_MODE INFERENCE_ENGINE

# If running TRT, ensure CUDA 13.x toolkit AND driver before heavy work
if [ "${INFERENCE_ENGINE:-trt}" = "trt" ]; then
  if ! trt_assert_cuda13_driver "restart"; then
    log_err "[cuda] CUDA 13.x required for TensorRT-LLM"
    exit 1
  fi
fi

# Validate --push-quant prerequisites early (before any heavy operations)
validate_push_quant_prereqs "${DEPLOY_MODE}"

# Check for engine switching - this requires FULL environment wipe
if runtime_guard_engine_changed "${INFERENCE_ENGINE}" "${ROOT_DIR}"; then
  last_engine="$(runtime_guard_read_last_config_value "INFERENCE_ENGINE" "${ROOT_DIR}")"
  log_warn "[restart] =========================================="
  log_warn "[restart] ENGINE SWITCH DETECTED: ${last_engine} → ${INFERENCE_ENGINE}"
  log_warn "[restart] =========================================="
  log_warn "[restart] Cannot hot-restart with different engine."
  log_warn "[restart] Running full deployment instead..."
  log_warn "[restart] =========================================="
  
  # Redirect to main.sh with the new engine
  exec bash "${SCRIPT_DIR}/main.sh" \
    "--${INFERENCE_ENGINE}" \
    "${DEPLOY_MODE}" \
    "${CHAT_MODEL:-}" \
    "${TOOL_MODEL:-}"
fi

log_info "[restart] Engine: ${INFERENCE_ENGINE}"

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
  log_error "[restart] No AWQ models found for deploy mode '${DEPLOY_MODE}'"
  log_error "[restart] "
  log_error "[restart] Options:"
  log_error "[restart] 1. Run full deployment first: bash scripts/main.sh 4bit <chat_model> <tool_model>"
  log_error "[restart] 2. Ensure cached AWQ exports exist in ${ROOT_DIR}/.awq/"
  exit 1
fi

# Check if venv exists (only required for local models or first run)
if [ ! -d "${ROOT_DIR}/.venv" ]; then
  log_error "[restart] No virtual environment found at ${ROOT_DIR}/.venv"
  log_error "[restart] For local models: Run full deployment first: bash scripts/main.sh 4bit <chat_model> <tool_model>"
  log_error "[restart] For HF or other remote models: run full deployment first to cache AWQ artifacts"
  exit 1
fi

# Optional dependency refresh
if [ "${INSTALL_DEPS}" = "1" ]; then
  log_info "[restart] Reinstalling all dependencies from scratch (--install-deps)"
  
  # Wipe all existing pip dependencies and caches for clean install
  # Preserves models, HF cache, TRT repo
  wipe_dependencies_for_reinstall
  
  # Ensure correct Python version is available (TRT needs 3.10, vLLM uses system python)
  # Explicitly pass INFERENCE_ENGINE to subprocess
  INFERENCE_ENGINE="${INFERENCE_ENGINE:-trt}" "${SCRIPT_DIR}/steps/02_python_env.sh" || {
    log_err "[restart] Failed to set up Python environment"
    exit 1
  }
  
  # Reinstall all dependencies from scratch (force mode)
  FORCE_REINSTALL=1 INFERENCE_ENGINE="${INFERENCE_ENGINE:-trt}" "${SCRIPT_DIR}/steps/03_install_deps.sh"
fi

# Report detected model sources
log_info "[restart] Detected model sources for restart:"
if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "chat" ]; then
  chat_origin="local cache"
  if [ "${CHAT_AWQ_SOURCE_KIND:-local}" != "local" ]; then
    chat_origin="pre-quantized repo"
  fi
  log_info "[restart]   Chat (${chat_origin}): ${CHAT_AWQ_SOURCE:-${CHAT_AWQ_DIR}}"
fi
if [ "${DEPLOY_MODE}" = "both" ] || [ "${DEPLOY_MODE}" = "tool" ]; then
  log_info "[restart]   Tool: classifier weights reused directly"
fi

# Light stop - preserve models and dependencies
log_info "[restart] Stopping server (preserving models and dependencies)..."
NUKE_ALL=0 "${SCRIPT_DIR}/stop.sh"

restart_setup_env_for_awq "${DEPLOY_MODE}"
restart_apply_defaults_and_deps
restart_push_cached_awq_models "${DEPLOY_MODE}"
restart_server_background
