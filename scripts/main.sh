#!/usr/bin/env bash
# =============================================================================
# Yap Text Inference Server - Main Entry Point
# =============================================================================
# Primary startup script for deploying the inference server. Handles GPU
# detection, model validation, quantization selection, and deployment
# pipeline orchestration for both vLLM and TensorRT-LLM engines.
#
# Usage: bash scripts/main.sh [--trt|--vllm] <deploy_mode> [quant] <models...>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Core utilities
source "${SCRIPT_DIR}/lib/noise/python.sh"
source "${SCRIPT_DIR}/lib/common/log.sh"
source "${SCRIPT_DIR}/lib/common/params.sh"
source "${SCRIPT_DIR}/lib/common/warmup.sh"
source "${SCRIPT_DIR}/lib/common/model_detect.sh"
source "${SCRIPT_DIR}/lib/common/model_validate.sh"
source "${SCRIPT_DIR}/lib/common/gpu_detect.sh"
source "${SCRIPT_DIR}/engines/trt/detect.sh"
source "${SCRIPT_DIR}/lib/common/cuda.sh"
source "${SCRIPT_DIR}/lib/common/cli.sh"
source "${SCRIPT_DIR}/lib/deps/venv.sh"
source "${SCRIPT_DIR}/lib/common/pytorch_guard.sh"

# Runtime management
source "${SCRIPT_DIR}/lib/runtime/restart_guard.sh"
source "${SCRIPT_DIR}/lib/runtime/pipeline.sh"

# Main script modules
source "${SCRIPT_DIR}/lib/main/usage.sh"
source "${SCRIPT_DIR}/lib/main/args.sh"
source "${SCRIPT_DIR}/lib/main/quant.sh"
source "${SCRIPT_DIR}/lib/main/deploy.sh"

log_info "[main] Starting Yap Text Inference Server"

ensure_required_env_vars

# Detect GPU and export arch flags early (needed for modelopt/TRT builds)
gpu_init_detection "gpu"
gpu_apply_env_defaults

# Stop any existing warmup processes before starting deployment
stop_existing_warmup_processes "${ROOT_DIR}"

# Parse command line arguments
if [ $# -lt 1 ]; then
  log_warn "[main] ⚠ Not enough arguments"
  show_usage
fi

if ! parse_cli "$@"; then
  show_usage
fi

# If running TRT, ensure CUDA 13.x toolkit AND driver before heavy work
ensure_cuda_ready_for_engine "main" || exit 1

# Torch/TorchVision mismatch causes runtime import errors; wipe mismatched wheels
torch_cuda_mismatch_guard "[main]"

# Export models to environment
export_models

# Validate --push-quant prerequisites early (before any heavy operations)
# NOTE: actual push enablement is deferred until quantization is resolved
if ! validate_push_quant_prequant "${CHAT_MODEL:-}" "${TOOL_MODEL:-}" "${HF_AWQ_PUSH_REQUESTED:-0}" "[main]"; then
  exit 1
fi

# Early model validation - fail fast before any heavy operations
log_info "[model] Validating model configuration..."
if ! validate_models_early; then
  log_err "[model] ✗ Aborting deployment due to invalid model configuration"
  exit 1
fi

# Determine quantization hint and apply selection
CHAT_QUANT_HINT="$(get_quant_hint)"
apply_quantization "${QUANT_TYPE}" "${CHAT_QUANT_HINT}"

# Enable/disable push based on quantization (only allow 4-bit exports)
push_quant_apply_policy "${CHAT_QUANTIZATION:-}" "main"
validate_push_quant_prereqs "${DEPLOY_MODE:-both}"

# Enable/disable engine push based on engine type (only TRT)
push_engine_apply_policy "${INFERENCE_ENGINE:-trt}" "main"
validate_push_engine_prereqs

# Snapshot desired config for smart restart detection
DESIRED_DEPLOY_MODE="${DEPLOY_MODE:-both}"
DESIRED_CHAT_MODEL="${CHAT_MODEL:-}"
DESIRED_TOOL_MODEL="${TOOL_MODEL:-}"
DESIRED_CHAT_QUANT="${CHAT_QUANTIZATION:-}"
DESIRED_ENGINE="${INFERENCE_ENGINE:-trt}"

# If the server is already running, decide whether to keep caches or reset.
# NOTE: Engine switch (vllm <-> trt) triggers FULL environment wipe automatically.
stop_server_if_needed \
  "${SCRIPT_DIR}" \
  "${ROOT_DIR}" \
  "${DESIRED_DEPLOY_MODE}" \
  "${DESIRED_CHAT_MODEL}" \
  "${DESIRED_TOOL_MODEL}" \
  "${DESIRED_CHAT_QUANT}" \
  "${DESIRED_ENGINE}"

# Display configuration and run deployment
log_deploy_config
run_deploy "${ROOT_DIR}" "${SCRIPT_DIR}"
