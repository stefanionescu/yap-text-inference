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

log_info "Setting environment defaults"

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

log_info "Configuration: GPU=${DETECTED_GPU_NAME:-unknown}"
log_info "Deploy mode: ${DEPLOY_MODELS} (chat=${DEPLOY_CHAT}, tool=${DEPLOY_TOOL})"
if [ "${DEPLOY_CHAT}" = "1" ]; then
  log_info "  Chat model: ${CHAT_MODEL:-<unset>}"
  chat_backend="${CHAT_QUANTIZATION:-${QUANTIZATION:-<unset>}}"
  log_info "  Chat quantization: ${QUANT_MODE:-auto} (backend=${chat_backend})"
fi
if [ "${DEPLOY_TOOL}" = "1" ]; then
  log_info "  Tool model: ${TOOL_MODEL:-<unset>}"
  log_info "  Tool runtime: classifier (PyTorch, float weights)"
fi
if [ "${DEPLOY_CHAT}" = "1" ]; then
  log_info "  KV dtype: ${KV_DTYPE}"
fi
