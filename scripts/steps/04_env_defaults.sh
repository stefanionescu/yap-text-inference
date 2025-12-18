#!/usr/bin/env bash
set -euo pipefail
THIS_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Respect existing ROOT_DIR when this file is sourced; fall back to repo root when executed directly
# Repo root is two levels up from steps/ when executed directly
ROOT_DIR="${ROOT_DIR:-$(cd "${THIS_SCRIPT_DIR}/../.." && pwd)}"
source "${THIS_SCRIPT_DIR}/../lib/common/log.sh"

# Shared library functions
LIB_DIR="${THIS_SCRIPT_DIR}/../lib"
source "${LIB_DIR}/env/detect.sh"
source "${LIB_DIR}/env/paths.sh"
source "${LIB_DIR}/env/quantization.sh"
source "${LIB_DIR}/env/deploy.sh"
source "${LIB_DIR}/env/limits.sh"
source "${LIB_DIR}/env/engine.sh"
source "${LIB_DIR}/env/awq.sh"
source "${THIS_SCRIPT_DIR}/../engines/trt/detect.sh"

# Validate CUDA 13.x for TRT before setting environment defaults
if [ "${INFERENCE_ENGINE:-vllm}" = "trt" ] || [ "${INFERENCE_ENGINE:-vllm}" = "TRT" ]; then
  if ! trt_assert_cuda13_driver "env"; then
    log_err "[cuda] CUDA 13.x required for TensorRT-LLM"
    exit 1
  fi
fi

log_info "[env] Setting environment defaults"

# Detect FlashInfer availability for runtime tuning (optional)
detect_flashinfer

setup_deploy_mode_and_validate || exit 1

apply_limits_and_timeouts

apply_engine_defaults

# Speed up subsequent installs and centralize caches under repo
set_repo_cache_paths

apply_awq_env || exit 1

# Backend selection remains centralized in Python; env override applied in apply_engine_defaults

# --- GPU detection and optimization ---
detect_gpu_name

# Apply GPU-/quantization-specific defaults
apply_quantization_defaults

log_info "[env] Configuration: GPU=${DETECTED_GPU_NAME:-unknown}"
if [ "${DEPLOY_CHAT}" = "1" ]; then
  chat_precision="${CHAT_QUANTIZATION:-${QUANTIZATION:-fp16}}"
  log_info "[env] Chat model: ${CHAT_MODEL:-<unset>} (${chat_precision})"
fi
if [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "[env] Tool model: ${TOOL_MODEL:-<unset>} (fp32)"
fi
