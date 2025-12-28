#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Engine Build Utilities
# =============================================================================
# Functions for building TensorRT-LLM engines from quantized checkpoints.

_TRT_BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common GPU detection (if not already sourced)
if ! type gpu_detect_name >/dev/null 2>&1; then
  source "${_TRT_BUILD_DIR}/../../lib/common/gpu_detect.sh"
fi

# =============================================================================
# ENGINE BUILD
# =============================================================================

# Build TensorRT-LLM engine from checkpoint
# Usage: trt_build_engine <checkpoint_dir> <engine_dir> [options...]
trt_build_engine() {
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
  
  # Validate checkpoint
  trt_validate_checkpoint "${checkpoint_dir}" || return 1
  
  # Check if engine already exists
  if [ -d "${engine_dir}" ] && ls "${engine_dir}"/rank*.engine >/dev/null 2>&1; then
    if [ "${FORCE_REBUILD:-false}" != "true" ]; then
      log_info "[build] Reusing existing engine at ${engine_dir}"
      return 0
    fi
    log_info "[build] FORCE_REBUILD=true, rebuilding engine..."
  fi
  
  log_info "[build] Building TensorRT-LLM engine..."
  log_info "[build]   Checkpoint: ${checkpoint_dir}"
  log_info "[build]   Output: ${engine_dir}"
  
  # Calculate max sequence length
  local max_seq_len=$((TRT_MAX_INPUT_LEN + TRT_MAX_OUTPUT_LEN))
  
  # Build the engine
  local build_cmd=(
    trtllm-build
    --checkpoint_dir "${checkpoint_dir}"
    --output_dir "${engine_dir}"
    --gemm_plugin auto
    --gpt_attention_plugin float16
    --context_fmha enable
    --kv_cache_type paged
    --remove_input_padding enable
    --max_input_len "${TRT_MAX_INPUT_LEN:-8192}"
    --max_seq_len "${max_seq_len}"
    --max_batch_size "${TRT_MAX_BATCH_SIZE:-16}"
    --log_level info
    --workers "$(nproc --all)"
  )
  
  "${build_cmd[@]}" || {
    log_err "[build] ✗ Engine build failed"
    return 1
  }
  
  # Validate engine was created
  if ! ls "${engine_dir}"/rank*.engine >/dev/null 2>&1; then
    log_err "[build] ✗ Engine build completed but no rank*.engine files found"
    return 1
  fi
  
  # Record build metadata
  trt_record_build_metadata "${engine_dir}" "${checkpoint_dir}"
  
  log_info "[build] ✓ Engine build complete: ${engine_dir}"
  return 0
}

# =============================================================================
# BUILD METADATA
# =============================================================================

# Record build command and metadata
trt_record_build_metadata() {
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
  --kv_cache_type paged \\
  --remove_input_padding enable \\
  --max_input_len ${TRT_MAX_INPUT_LEN:-8192} \\
  --max_seq_len $((TRT_MAX_INPUT_LEN + TRT_MAX_OUTPUT_LEN)) \\
  --max_batch_size ${TRT_MAX_BATCH_SIZE:-16} \\
  --log_level info
EOF
  chmod +x "${cmd_file}"
  
  # Get TensorRT-LLM version (suppress TRT-LLM's import banner by only taking last line)
  local trtllm_ver
  trtllm_ver=$(python -c "import tensorrt_llm; print(tensorrt_llm.__version__)" 2>/dev/null | tail -n1 || echo "unknown")
  
  # Get CUDA version
  local cuda_ver
  cuda_ver=$(trt_detect_cuda_version 2>/dev/null || echo "unknown")
  
  # Get GPU info
  local gpu_name
  gpu_name=$(gpu_detect_name 2>/dev/null || echo "unknown")
  
  local gpu_vram
  gpu_vram=$(gpu_detect_vram_gb 2>/dev/null || echo "0")
  
  # Get NVIDIA driver version
  local nvidia_driver
  nvidia_driver=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -n1 || echo "unknown")
  
  # Determine quantization info from checkpoint config
  local quant_info="{}"
  if [ -f "${checkpoint_dir}/config.json" ]; then
    quant_info=$(python -c "
import json
with open('${checkpoint_dir}/config.json') as f:
    cfg = json.load(f)
quant = cfg.get('quantization', {})
print(json.dumps(quant))
" 2>/dev/null || echo "{}")
  fi
  
  # Determine KV cache dtype based on quantization format
  local kv_cache_dtype="int8"
  case "${TRT_QFORMAT:-int4_awq}" in
    fp8) kv_cache_dtype="fp8" ;;
    *) kv_cache_dtype="int8" ;;
  esac
  
  # Write metadata
  local meta_file="${engine_dir}/build_metadata.json"
{
  "model_id": "${CHAT_MODEL:-unknown}",
  "dtype": "${TRT_DTYPE:-float16}",
  "max_batch_size": ${TRT_MAX_BATCH_SIZE:-16},
  "max_input_len": ${TRT_MAX_INPUT_LEN:-8192},
  "max_output_len": ${TRT_MAX_OUTPUT_LEN:-4096},
  "quantization": ${quant_info},
  "tensorrt_llm_version": "${trtllm_ver}",
  "cuda_toolkit": "${cuda_ver}",
  "sm_arch": "${GPU_SM_ARCH:-unknown}",
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
  
  log_info "[build] Build metadata recorded to ${meta_file}"
}

# =============================================================================
# ENGINE VALIDATION
# =============================================================================

# Validate TensorRT-LLM engine directory
trt_validate_engine() {
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
  
  local engine_count
  engine_count=$(ls "${engine_dir}"/rank*.engine 2>/dev/null | wc -l)
  log_info "[build] ✓ Engine validated (${engine_count} file(s)): ${engine_dir}"
  return 0
}

# =============================================================================
# FULL BUILD PIPELINE
# =============================================================================

# Complete quantization and build pipeline
# Usage: trt_quantize_and_build <model_id> [qformat]
trt_quantize_and_build() {
  local model_id="${1:-}"
  local qformat="${2:-}"
  
  if [ -z "${model_id}" ]; then
    log_err "[build] ✗ Model ID is required"
    return 1
  fi
  
  # Resolve qformat (pass model_id for MoE detection)
  if [ -z "${qformat}" ]; then
    qformat=$(trt_resolve_qformat "${QUANTIZATION:-4bit}" "${GPU_SM_ARCH:-}" "${model_id}")
  fi
  
  log_info "[build] Starting TRT quantize and build pipeline..."
  log_info "[build]   Model: ${model_id}"
  log_info "[build]   Format: ${qformat}"
  log_info "[build]   GPU: ${GPU_SM_ARCH:-auto} ($(gpu_detect_name))"
  
  # Check if this is a pre-quantized model
  if trt_is_prequantized_model "${model_id}"; then
    log_info "[build] Detected pre-quantized TRT model"
    local ckpt_dir
    ckpt_dir=$(trt_download_prequantized "${model_id}") || return 1
    TRT_CHECKPOINT_DIR="${ckpt_dir}"
  else
    # Quantize the model
    local ckpt_dir
    ckpt_dir=$(trt_get_checkpoint_dir "${model_id}" "${qformat}")
    trt_quantize_model "${model_id}" "${ckpt_dir}" "${qformat}" || return 1
    TRT_CHECKPOINT_DIR="${ckpt_dir}"
  fi
  
  # Build engine
  local engine_dir
  engine_dir=$(trt_get_engine_dir "${model_id}" "${qformat}")
  trt_build_engine "${TRT_CHECKPOINT_DIR}" "${engine_dir}" || return 1
  
  # Export engine directory for server
  TRT_ENGINE_DIR="${engine_dir}"
  export TRT_ENGINE_DIR TRT_CHECKPOINT_DIR
  
  # Save engine dir for later use
  mkdir -p "${ROOT_DIR:-.}/.run"
  echo "export TRTLLM_ENGINE_DIR='${TRT_ENGINE_DIR}'" > "${ROOT_DIR:-.}/.run/trt_engine_dir.env"
  
  log_info "[build] ✓ Pipeline complete: ${TRT_ENGINE_DIR}"
  
  return 0
}
