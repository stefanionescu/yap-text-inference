#!/usr/bin/env bash
# =============================================================================
# Runtime Cleanup - Tmp and Runtime State
# =============================================================================

cleanup_runtime_state() {
  local root_dir="$1"
  if [ -d "${root_dir}/.run" ]; then
    rm -rf "${root_dir}/.run"
  fi
}

cleanup_tmp_dirs() {
  rm -rf \
    /tmp/vllm* /tmp/flashinfer* /tmp/torch_* /tmp/pip-* /tmp/pip-build-* \
    /tmp/pip-modern-metadata-* /tmp/uvicorn* /tmp/trtllm* /tmp/trt* \
    /tmp/tensorrt* /tmp/nv* /tmp/hf* /tmp/cuda* /tmp/modelopt* /tmp/quantiz* 2>/dev/null || true
  rm -rf /dev/shm/tensorrt* /dev/shm/trt* /dev/shm/torch* /dev/shm/nv* /dev/shm/cuda* /dev/shm/hf* 2>/dev/null || true
}

cleanup_python_artifacts() {
  local root_dir="$1"
  find "${root_dir}" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
  find "${root_dir}" -type d -name ".pytest_cache" -prune -exec rm -rf {} + 2>/dev/null || true
}
