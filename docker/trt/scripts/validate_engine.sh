#!/usr/bin/env bash
# shellcheck disable=SC1091

# Validate that the baked-in TRT engine is compatible with the runtime GPU.
# Compares sm_arch from build_metadata.json with the detected GPU's SM architecture.
#
# Validation:
# - Missing build_metadata.json → ERROR
# - Cannot detect runtime GPU → ERROR
# - SM arch mismatch → ERROR
# - Tool-only deployment (no engine) → SKIP

_VALIDATE_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "/app/common/scripts/logs.sh"
ROOT_DIR="${ROOT_DIR:-$(cd "${_VALIDATE_SCRIPT_DIR}/../../.." && pwd)}"

validate_engine_gpu_compatibility() {
  local engine_dir="${TRT_ENGINE_DIR:-/opt/engines/trt-chat}"
  local metadata_file="${engine_dir}/build_metadata.json"
  local deploy_chat="${DEPLOY_CHAT:-0}"

  # Tool-only images intentionally have no chat engine.
  if [ "${deploy_chat}" != "1" ]; then
    log_info "[validate] DEPLOY_CHAT=0 - skipping TRT engine validation"
    return 0
  fi

  # Chat deployments must have a real engine directory.
  if [ ! -d "${engine_dir}" ]; then
    log_err "[validate] ✗ TRT engine directory not found: ${engine_dir}"
    return 1
  fi

  # Chat deployments must include engine files.
  if ! ls "${engine_dir}"/rank*.engine >/dev/null 2>&1; then
    log_err "[validate] ✗ No TRT engine files found in ${engine_dir}"
    return 1
  fi

  # STRICT: Require metadata file
  if [ ! -f "${metadata_file}" ]; then
    log_err "[validate] ✗ Missing engine metadata"
    return 1
  fi

  # Get the SM arch from metadata
  local engine_sm_arch=""
  local engine_gpu_name=""

  if command -v python3 >/dev/null 2>&1; then
    engine_sm_arch=$(PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
      python3 -m src.scripts.validation.metadata "${metadata_file}" sm_arch 2>/dev/null) || true

    # shellcheck disable=SC2034  # Reserved for future validation
    engine_gpu_name=$(PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
      python3 -m src.scripts.validation.metadata "${metadata_file}" gpu_name 2>/dev/null) || true
  fi

  # STRICT: Require sm_arch in metadata
  if [ -z "${engine_sm_arch}" ]; then
    log_err "[validate] ✗ Invalid engine metadata: missing sm_arch"
    return 1
  fi

  # Get the current GPU's SM arch (already set by gpu_detect.sh)
  local runtime_sm_arch="${GPU_SM_ARCH:-}"

  # STRICT: Require runtime GPU detection
  if [ -z "${runtime_sm_arch}" ]; then
    log_err "[validate] ✗ Cannot detect runtime GPU"
    return 1
  fi

  # Compare SM architectures
  if [ "${engine_sm_arch}" != "${runtime_sm_arch}" ]; then
    log_err "[validate] ✗ GPU mismatch: engine=${engine_sm_arch}, runtime=${runtime_sm_arch}"
    return 1
  fi

  log_info "[validate] ✓ GPU compatibility verified: ${engine_sm_arch} (${DETECTED_GPU_NAME:-unknown})"
  return 0
}

# Run validation
if ! validate_engine_gpu_compatibility; then
  log_err "[validate] Engine/GPU compatibility check failed. Aborting."
  exit 1
fi
