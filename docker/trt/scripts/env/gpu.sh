#!/usr/bin/env bash
# shellcheck disable=SC1091
# TRT GPU detection and optimization.
#
# Sources shared GPU detection from common/ and applies TRT-specific defaults.

_GPU_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find common scripts directory (works in Docker and dev contexts)
if [ -d "/app/common/scripts" ]; then
  _GPU_COMMON_SCRIPTS="/app/common/scripts"
elif [ -d "${_GPU_SCRIPT_DIR}/../../../common/scripts" ]; then
  _GPU_COMMON_SCRIPTS="${_GPU_SCRIPT_DIR}/../../../common/scripts"
else
  echo "[trt] ERROR: Cannot find common scripts directory" >&2
  exit 1
fi

# Source shared GPU detection
source "${_GPU_COMMON_SCRIPTS}/gpu.sh"

# Initialize GPU detection
gpu_init_detection
gpu_apply_env_defaults

# Export GPU_SM for artifact resolution (removes "sm" prefix for compatibility)
if [ -n "${GPU_SM_ARCH:-}" ]; then
  export GPU_SM="${GPU_SM_ARCH}"
fi

# TRT-specific GPU optimizations
GPU_NAME="${DETECTED_GPU_NAME:-}"

case "${GPU_NAME}" in
  *H100*)
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
    export PYTORCH_ALLOC_CONF=expandable_segments:True
    ;;
  *L40S* | *L40*)
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
    export PYTORCH_ALLOC_CONF=expandable_segments:True
    ;;
  *A100*)
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
    export PYTORCH_ALLOC_CONF=expandable_segments:True
    export CUDA_DEVICE_MAX_CONNECTIONS=1
    ;;
  *)
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
    ;;
esac
