#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/lib/noise/python.sh"
source "${SCRIPT_DIR}/lib/common/log.sh"
source "${SCRIPT_DIR}/lib/common/params.sh"
source "${SCRIPT_DIR}/lib/common/warmup.sh"
source "${SCRIPT_DIR}/lib/deps/venv.sh"
source "${SCRIPT_DIR}/lib/runtime/restart_guard.sh"
source "${SCRIPT_DIR}/lib/runtime/pipeline.sh"
source "${SCRIPT_DIR}/lib/common/model_validate.sh"
source "${SCRIPT_DIR}/lib/common/cli.sh"
source "${SCRIPT_DIR}/lib/common/pytorch_guard.sh"
source "${SCRIPT_DIR}/lib/restart/overrides.sh"
source "${SCRIPT_DIR}/lib/restart/args.sh"
source "${SCRIPT_DIR}/lib/restart/basic.sh"
source "${SCRIPT_DIR}/lib/restart/reconfigure.sh"
source "${SCRIPT_DIR}/lib/restart/awq.sh"
source "${SCRIPT_DIR}/lib/env/restart.sh"
source "${SCRIPT_DIR}/lib/restart/launch.sh"
source "${SCRIPT_DIR}/engines/vllm/push.sh"
source "${SCRIPT_DIR}/engines/trt/push.sh"
source "${SCRIPT_DIR}/engines/trt/detect.sh"
source "${SCRIPT_DIR}/lib/common/gpu_detect.sh"
source "${SCRIPT_DIR}/lib/common/cuda.sh"

log_info "[restart] Restarting server..."

ensure_required_env_vars

# Resolve venv path the same way main does (supports baked /opt/venv)
export VENV_DIR="${VENV_DIR:-$(get_venv_dir)}"

# Detect GPU and export arch flags early
gpu_init_detection "gpu"
gpu_apply_env_defaults

# Stop any existing warmup processes before restarting
stop_existing_warmup_processes "${ROOT_DIR}"

usage() {
  cat <<'USAGE'
Usage:
  restart.sh <deploy_mode> [--trt|--vllm] [--install-deps] [--keep-models]
      Quick restart that reuses existing quantized caches (default behavior).
      NOTE: deploy_mode (both|chat|tool) is REQUIRED.

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

Deploy modes (REQUIRED):
  both            - Deploy chat + tool engines
  chat            - Deploy chat-only
  tool            - Deploy tool-only

Key flags:
  --install-deps        Reinstall dependencies inside .venv before restart
  --reset-models        Delete cached models/HF data and redeploy new models
  --keep-models         Reuse existing quantized caches (default)
  --push-quant          Upload cached 4-bit exports to Hugging Face before relaunch
  --push-engine         Push locally-built TRT engine to source HF repo (prequant models only)
  --chat-model <repo>   Chat model to deploy (required with --reset-models chat/both)
  --tool-model <repo>   Tool model to deploy (required with --reset-models tool/both)
  --chat-quant <val>    Override chat/base quantization (4bit|8bit|fp8|gptq|gptq_marlin|awq).
                        `4bit` uses NVFP4 for MoE models (TRT) or AWQ for dense models.
                        `8bit` uses FP8 (L40S/H100) or INT8-SQ (A100).
                        Pre-quantized repos are detected automatically.
  --show-hf-logs        Show Hugging Face download/upload progress bars
  --show-trt-logs       Show TensorRT-LLM build/quantization logs
  --show-llmcompressor-logs   Show LLMCompressor/AutoAWQ calibration progress

This script always:
  • Stops the server
  • Preserves the repository and container
  • Keeps dependencies unless --install-deps or stop.sh removes them

Required environment variables:
  TEXT_API_KEY, HF_TOKEN (or HUGGINGFACE_HUB_TOKEN), MAX_CONCURRENT_CONNECTIONS

Examples:
  bash scripts/restart.sh both             # TRT engine with existing caches
  bash scripts/restart.sh --vllm both      # Switch to vLLM (triggers full wipe)
  bash scripts/restart.sh chat             # Chat-only restart
  bash scripts/restart.sh tool --install-deps  # Tool-only with deps reinstall
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
case "${DEPLOY_MODE}" in both|chat|tool) : ;; *) log_warn "[restart] ⚠ Invalid deploy mode '${DEPLOY_MODE}'"; usage ;; esac
export INSTALL_DEPS DEPLOY_MODE INFERENCE_ENGINE

# If running TRT, ensure CUDA 13.x toolkit AND driver before heavy work
ensure_cuda_ready_for_engine "restart" || exit 1

# Torch/TorchVision mismatch causes runtime import errors; remove mismatched wheels
torch_cuda_mismatch_guard "[restart]"
if [ "${TORCHVISION_CUDA_MISMATCH_DETECTED:-0}" = "1" ] && [ "${INSTALL_DEPS:-0}" != "1" ]; then
  log_info "[restart] torch/torchvision mismatch detected; forcing --install-deps for clean reinstall"
  INSTALL_DEPS=1
  export INSTALL_DEPS
fi

# Validate --push-quant prerequisites early (before any heavy operations)
# Check for engine switching - this requires FULL environment wipe
# Uses unified handler to avoid duplicate logic with main.sh
ENGINE_SWITCH_RESULT=0
runtime_guard_handle_engine_switch "${SCRIPT_DIR}" "${ROOT_DIR}" "${INFERENCE_ENGINE}" || ENGINE_SWITCH_RESULT=$?

if [ "${ENGINE_SWITCH_RESULT}" = "2" ]; then
  log_err "[restart] ✗ Engine switch failed"
  exit 1
fi

# If engine was switched, need full deployment (restart can't handle fresh engine)
if [ "${ENGINE_SWITCH_RESULT}" = "0" ]; then
  # Build main.sh args using shared flag builder
  args_build_forward_flags
  declare -a main_args=("--${INFERENCE_ENGINE}" "--deploy-mode" "${DEPLOY_MODE}")
  main_args+=("${ARGS_FORWARD_FLAGS[@]}")

  # Pass quantization if specified
  if [ -n "${RECONFIG_CHAT_QUANTIZATION:-}" ]; then
    case "${RECONFIG_CHAT_QUANTIZATION}" in
      4bit|4BIT) main_args+=("4bit") ;;
      8bit|8BIT) main_args+=("8bit") ;;
    esac
  fi

  # Add model(s) based on deploy mode
  case "${DEPLOY_MODE}" in
    chat)
      main_args+=("${RECONFIG_CHAT_MODEL:-${CHAT_MODEL:-}}")
      ;;
    tool)
      main_args+=("${RECONFIG_TOOL_MODEL:-${TOOL_MODEL:-}}")
      ;;
    both)
      main_args+=("${RECONFIG_CHAT_MODEL:-${CHAT_MODEL:-}}")
      main_args+=("${RECONFIG_TOOL_MODEL:-${TOOL_MODEL:-}}")
      ;;
  esac

  exec bash "${SCRIPT_DIR}/main.sh" "${main_args[@]}"
fi

log_section "[restart] Engine: ${INFERENCE_ENGINE}"

if [ "${RESTART_MODEL_MODE}" = "reconfigure" ]; then
  restart_reconfigure_models
  exit 0
fi

# Generic path may start and tail the server; if not applicable, it returns
restart_basic
restart_detect_awq_models "${DEPLOY_MODE}"

# Validate --push-quant is not used with prequantized models (non-reconfigure path)
if [ "${HF_AWQ_PUSH_REQUESTED:-0}" = "1" ] && [ "${CHAT_AWQ_SOURCE_KIND:-}" = "prequant" ]; then
  log_err "[restart] ✗ Cannot use --push-quant with a prequantized model."
  log_err "[restart]   Model '${CHAT_AWQ_SOURCE:-}' is already quantized."
  log_err "[restart]   There are no local quantization artifacts to upload."
  log_blank
  log_err "[restart]   Options:"
  log_err "[restart]     1. Remove --push-quant to use the prequantized model directly"
  log_err "[restart]     2. Use a base (non-quantized) model if you want to quantize and push"
  exit 1
fi

# Validate we have at least one valid source
if [ "${AWQ_SOURCES_READY:-0}" != "1" ]; then
  log_err "[restart] ✗ No AWQ models found for deploy mode '${DEPLOY_MODE}'"
  log_blank
  log_err "[restart] Options:"
  log_err "[restart]   1. Run full deployment first: bash scripts/main.sh 4bit <chat_model> <tool_model>"
  log_err "[restart]   2. Ensure cached AWQ exports exist in ${ROOT_DIR}/.awq/"
  exit 1
fi

# Light stop - preserve models and dependencies (BEFORE deps install)
log_section "[restart] Stopping server..."
NUKE_ALL=0 "${SCRIPT_DIR}/stop.sh"

# Check if venv exists (skip if --install-deps will create it)
venv_dir="${VENV_DIR:-$(get_venv_dir)}"
if [ "${INSTALL_DEPS:-0}" != "1" ] && [ ! -d "${venv_dir}" ]; then
  log_err "[restart] ✗ No virtual environment found at ${venv_dir}"
  log_err "[restart] ✗ Run with --install-deps to create it, or run full deployment first"
  exit 1
fi

restart_setup_env_for_awq "${DEPLOY_MODE}"
# Enable/disable push now that quantization is set (only allow 4-bit exports)
push_quant_apply_policy "${QUANTIZATION:-}" "${CHAT_QUANTIZATION:-}" "restart"
validate_push_quant_prereqs "${DEPLOY_MODE}"
# Enable/disable engine push based on engine type (only TRT)
push_engine_apply_policy "${INFERENCE_ENGINE:-trt}" "restart"
validate_push_engine_prereqs
restart_validate_awq_push_prereqs "${DEPLOY_MODE}"
# Validate model selections early for AWQ path before heavy work
if ! validate_models_early; then
  exit 1
fi
# NOTE: restart_apply_defaults_and_deps handles --install-deps for AWQ path
restart_apply_defaults_and_deps
restart_push_cached_awq_models "${DEPLOY_MODE}"

# TRT engine: validate engine directory exists before starting server
if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ] && [ "${DEPLOY_MODE}" != "tool" ]; then
  if [ -z "${TRT_ENGINE_DIR:-}" ] || [ ! -d "${TRT_ENGINE_DIR:-}" ]; then
    log_err "[restart] ✗ TRT engine directory not found or not set."
    log_err "[restart]   TRT_ENGINE_DIR='${TRT_ENGINE_DIR:-<empty>}'"
    log_blank
    log_err "[restart]   TensorRT-LLM requires a pre-built engine. Options:"
    log_err "[restart]     1. Build TRT engine first: bash scripts/quantization/trt_quantizer.sh <model>"
    log_err "[restart]     2. Use vLLM instead: bash scripts/restart.sh --vllm ${DEPLOY_MODE}"
    log_err "[restart]     3. Or run full deployment: bash scripts/main.sh --trt <deploy_mode> <model>"
    exit 1
  fi
  log_info "[restart] ✓ TRT engine validated"
  log_blank
fi

restart_server_background
