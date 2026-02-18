#!/usr/bin/env bash
# shellcheck disable=SC1091
# =============================================================================
# TRT-LLM Engine Build Utilities
# =============================================================================
# Functions for building TensorRT-LLM engines from quantized checkpoints.

_TRT_BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common GPU detection (if not already sourced)
if ! type get_gpu_name >/dev/null 2>&1; then
  source "${_TRT_BUILD_DIR}/../../lib/common/gpu_detect.sh"
fi

# Source TRT detection utilities (for pre-built engine discovery)
if ! type find_compatible_engine >/dev/null 2>&1; then
  source "${_TRT_BUILD_DIR}/detect.sh"
fi

if ! type is_trt_prequant >/dev/null 2>&1; then
  source "${_TRT_BUILD_DIR}/../../lib/common/model_detect.sh"
fi

if ! type trt_pipeline_run >/dev/null 2>&1; then
  source "${_TRT_BUILD_DIR}/../../lib/trt/pipeline.sh"
fi

# =============================================================================
# ENGINE BUILD
# =============================================================================

# Build TensorRT-LLM engine from checkpoint
# Usage: build_engine <checkpoint_dir> <engine_dir> [options...]
build_engine() {
  local checkpoint_dir="${1:-}"
  local engine_dir="${2:-}"

  if [ -z "${checkpoint_dir}" ]; then
    log_err "[build] ✗ Checkpoint directory is required"
    return 1
  fi

  if [ -z "${engine_dir}" ]; then
    log_err "[build] ✗ Engine output directory is required"
    return 1
  fi

  # Check if engine already exists
  if [ -d "${engine_dir}" ] && ls "${engine_dir}"/rank*.engine >/dev/null 2>&1; then
    if [ "${FORCE_REBUILD:-false}" != "true" ]; then
      log_info "[build] Reusing existing engine at ${engine_dir}"
      return 0
    fi
    log_info "[build] FORCE_REBUILD=true, rebuilding engine..."
  fi

  log_info "[build] Building TensorRT-LLM engine..."

  # Calculate max sequence length
  local max_seq_len=$((TRT_MAX_INPUT_LEN + TRT_MAX_OUTPUT_LEN))

  # Suppress TRT-LLM log noise via environment
  export TRTLLM_LOG_LEVEL="${TRTLLM_LOG_LEVEL:-error}"
  export PYTHONWARNINGS="${PYTHONWARNINGS:-ignore}"

  # Build the engine
  local build_cmd=(
    trtllm-build
    --checkpoint_dir "${checkpoint_dir}"
    --output_dir "${engine_dir}"
    --gemm_plugin auto
    --gpt_attention_plugin float16
    --context_fmha enable
    --use_paged_context_fmha enable
    --kv_cache_type paged
    --remove_input_padding enable
    --max_input_len "${TRT_MAX_INPUT_LEN:-8192}"
    --max_seq_len "${max_seq_len}"
    --max_batch_size "${TRT_MAX_BATCH_SIZE:-16}"
    --log_level error
    --workers "$(nproc --all)"
  )

  "${build_cmd[@]}" 2>&1 | grep -v -E '^\[.*\] \[TRT-LLM\] \[(I|W)\]|^\[TensorRT-LLM\]|WARNING.*Python version.*below the recommended' || true
  local build_status=${PIPESTATUS[0]}

  if [ "${build_status}" -ne 0 ]; then
    log_err "[build] ✗ Engine build failed"
    return 1
  fi

  # Validate engine was created
  if ! ls "${engine_dir}"/rank*.engine >/dev/null 2>&1; then
    log_err "[build] ✗ Engine build completed but no rank*.engine files found"
    return 1
  fi

  # Record build metadata
  record_build_metadata "${engine_dir}" "${checkpoint_dir}"

  log_info "[build] ✓ Engine build complete"
  return 0
}

# =============================================================================
# BUILD METADATA
# =============================================================================

# Record build command and metadata
record_build_metadata() {
  local engine_dir="${1:-}"
  local checkpoint_dir="${2:-}"

  mkdir -p "${engine_dir}"

  # Record build command
  local cmd_file="${engine_dir}/build_command.sh"
  cat >"${cmd_file}" <<EOF
#!/usr/bin/env bash
trtllm-build \\
  --checkpoint_dir "${checkpoint_dir}" \\
  --output_dir "${engine_dir}" \\
  --gemm_plugin auto \\
  --gpt_attention_plugin float16 \\
  --context_fmha enable \\
  --use_paged_context_fmha enable \\
  --kv_cache_type paged \\
  --remove_input_padding enable \\
  --max_input_len ${TRT_MAX_INPUT_LEN:-8192} \\
  --max_seq_len $((TRT_MAX_INPUT_LEN + TRT_MAX_OUTPUT_LEN)) \\
  --max_batch_size ${TRT_MAX_BATCH_SIZE:-16} \\
  --log_level error
EOF
  chmod +x "${cmd_file}"

  # Get TensorRT-LLM version (uses cached TRTLLM_INSTALLED_VERSION if available)
  local trtllm_ver
  trtllm_ver=$(detect_trtllm_version 2>/dev/null)
  if [ -z "${trtllm_ver}" ] || [ "${trtllm_ver}" = "unknown" ]; then
    log_err "[build] ✗ Cannot determine TensorRT-LLM version. Is tensorrt_llm installed?"
    return 1
  fi

  # Get CUDA version (uses CUDA_VERSION env var if set)
  local cuda_ver
  cuda_ver=$(detect_cuda_version 2>/dev/null)
  if [ -z "${cuda_ver}" ]; then
    log_err "[build] ✗ Cannot determine CUDA version. Is CUDA installed?"
    return 1
  fi

  # Get GPU info (uses DETECTED_GPU_NAME if already set)
  local gpu_name
  gpu_name="${DETECTED_GPU_NAME:-$(get_gpu_name 2>/dev/null)}"
  if [ -z "${gpu_name}" ] || [ "${gpu_name}" = "Unknown" ]; then
    log_err "[build] ✗ Cannot detect GPU. Is nvidia-smi available?"
    return 1
  fi

  local gpu_vram
  gpu_vram=$(detect_vram_gb 2>/dev/null || echo "0")

  # Get NVIDIA driver version
  local nvidia_driver
  nvidia_driver=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -n1 || echo "unknown")

  # Determine quantization info from checkpoint config
  local quant_info="{}"
  if [ -f "${checkpoint_dir}/config.json" ]; then
    local python_root="${ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
    quant_info=$(PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" \
      python -m src.scripts.trt.detection quant-info "${checkpoint_dir}" 2>/dev/null || echo "{}")
  fi

  # Determine KV cache dtype based on quantization format
  local kv_cache_dtype="int8"
  case "${TRT_QFORMAT:-int4_awq}" in
    fp8) kv_cache_dtype="fp8" ;;
    *) kv_cache_dtype="int8" ;;
  esac

  # Validate GPU_SM_ARCH is set (should be exported by gpu_init_detection)
  if [ -z "${GPU_SM_ARCH:-}" ]; then
    log_err "[build] ✗ GPU_SM_ARCH not set. Run gpu_init_detection() first."
    return 1
  fi

  # Write metadata
  local meta_file="${engine_dir}/build_metadata.json"
  cat >"${meta_file}" <<EOF
{
  "model_id": "${CHAT_MODEL:-unknown}",
  "dtype": "${TRT_DTYPE:-float16}",
  "quant_method": "${TRT_QFORMAT:-int4_awq}",
  "max_batch_size": ${TRT_MAX_BATCH_SIZE:-16},
  "max_input_len": ${TRT_MAX_INPUT_LEN:-8192},
  "max_output_len": ${TRT_MAX_OUTPUT_LEN:-4096},
  "quantization": ${quant_info},
  "tensorrt_llm_version": "${trtllm_ver}",
  "cuda_toolkit": "${cuda_ver}",
  "sm_arch": "${GPU_SM_ARCH}",
  "gpu_name": "${gpu_name}",
  "gpu_vram_gb": ${gpu_vram},
  "nvidia_driver": "${nvidia_driver}",
  "kv_cache_dtype": "${kv_cache_dtype}",
  "awq_block_size": ${TRT_AWQ_BLOCK_SIZE:-128},
  "calib_size": ${TRT_CALIB_SIZE:-256},
  "calib_batch_size": ${TRT_CALIB_BATCH_SIZE:-16},
  "built_at": "$(date -Iseconds)"
}
EOF
}

# =============================================================================
# ENGINE VALIDATION
# =============================================================================

# Validate TensorRT-LLM engine directory
validate_engine() {
  local engine_dir="${1:-${TRT_ENGINE_DIR:-}}"

  if [ -z "${engine_dir}" ]; then
    log_err "[build] ✗ Engine directory is required"
    return 1
  fi

  if [ ! -d "${engine_dir}" ]; then
    log_err "[build] ✗ Engine directory not found: ${engine_dir}"
    return 1
  fi

  # Check for engine files
  if ! ls "${engine_dir}"/rank*.engine >/dev/null 2>&1; then
    log_err "[build] ✗ No rank*.engine files found in ${engine_dir}"
    return 1
  fi

  log_info "[build] ✓ Engine validated"
  return 0
}

# =============================================================================
# FULL BUILD PIPELINE
# =============================================================================

# Complete quantization and build pipeline
# Usage: quantize_and_build <model_id> [qformat]
quantize_and_build() {
  local model_id="${1:-}"
  local qformat="${2:-}"

  if [ -z "${model_id}" ]; then
    log_err "[build] ✗ Model ID is required"
    return 1
  fi

  # Load remaining TRT modules required by the shared pipeline when needed.
  if ! type trt_prepare_repo >/dev/null 2>&1; then
    source "${_TRT_BUILD_DIR}/../../lib/trt/install.sh"
  fi
  if ! type quantize_model >/dev/null 2>&1; then
    source "${_TRT_BUILD_DIR}/quantize.sh"
  fi
  if ! type push_to_hf >/dev/null 2>&1; then
    source "${_TRT_BUILD_DIR}/push.sh"
  fi

  export INFERENCE_ENGINE="trt"
  export DEPLOY_CHAT=1
  export CHAT_MODEL="${model_id}"

  if [ -n "${qformat}" ]; then
    trt_export_quant_env "${qformat}"
    case "${qformat}" in
      int4_awq) CHAT_QUANTIZATION=4bit ;;
      fp8 | int8_sq) CHAT_QUANTIZATION=8bit ;;
      *) CHAT_QUANTIZATION="${qformat}" ;;
    esac
    export CHAT_QUANTIZATION
  fi

  trt_pipeline_run
}
