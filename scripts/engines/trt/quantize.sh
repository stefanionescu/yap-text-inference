#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Quantization Utilities
# =============================================================================
# Functions for quantizing models with TensorRT-LLM.

# =============================================================================
# MODEL DOWNLOAD
# =============================================================================

# Download model from HuggingFace to local directory
trt_download_model() {
  local model_id="${1:-}"
  local target_dir="${2:-}"
  
  if [ -z "${model_id}" ]; then
    log_err "Model ID is required"
    return 1
  fi
  
  # If model_id is a local path, use it directly
  if [ -d "${model_id}" ]; then
    echo "${model_id}"
    return 0
  fi
  
  # Determine target directory
  if [ -z "${target_dir}" ]; then
    local model_name
    model_name=$(basename "${model_id}")
    target_dir="${TRT_MODELS_DIR:-${ROOT_DIR:-.}/models}/${model_name}-hf"
  fi
  
  # Download if not already present
  if [ -d "${target_dir}" ] && [ -f "${target_dir}/config.json" ]; then
    log_info "Using cached model at ${target_dir}"
    echo "${target_dir}"
    return 0
  fi
  
  log_info "Downloading model ${model_id} to ${target_dir}"
  mkdir -p "${target_dir}"
  
  export HF_HUB_ENABLE_HF_TRANSFER=1
  python -c "
from huggingface_hub import snapshot_download
snapshot_download(repo_id='${model_id}', local_dir='${target_dir}', local_dir_use_symlinks=False)
print('✓ Downloaded model')
" || {
    log_err "Failed to download model ${model_id}"
    return 1
  }
  
  echo "${target_dir}"
}

# =============================================================================
# QUANTIZATION
# =============================================================================

# Quantize a model to TRT-LLM checkpoint format
# Usage: trt_quantize_model <model_id> <output_dir> [qformat]
trt_quantize_model() {
  local model_id="${1:-}"
  local output_dir="${2:-}"
  local qformat="${3:-}"
  
  if [ -z "${model_id}" ]; then
    log_err "Model ID is required"
    return 1
  fi
  
  if [ -z "${output_dir}" ]; then
    log_err "Output directory is required"
    return 1
  fi
  
  # Resolve qformat if not specified
  if [ -z "${qformat}" ]; then
    qformat=$(trt_resolve_qformat "${QUANTIZATION:-4bit}" "${GPU_SM_ARCH:-}")
  fi
  
  local kv_cache_dtype
  kv_cache_dtype=$(trt_resolve_kv_cache_dtype "${qformat}")
  
  log_info "Quantizing model ${model_id} to ${qformat}"
  log_info "Output directory: ${output_dir}"
  log_info "KV cache dtype: ${kv_cache_dtype}"
  
  # Check if already quantized
  if [ -d "${output_dir}" ] && [ -f "${output_dir}/config.json" ]; then
    if [ "${FORCE_REBUILD:-false}" != "true" ]; then
      log_info "Reusing existing checkpoint at ${output_dir}"
      return 0
    fi
    log_info "FORCE_REBUILD=true, re-quantizing..."
  fi
  
  # Download model if needed
  local local_model_dir
  local_model_dir=$(trt_download_model "${model_id}") || return 1
  
  # Get the appropriate quantization script
  local quant_script
  quant_script=$(trt_get_quantize_script "${model_id}" "${TRT_REPO_DIR}")
  
  if [ ! -f "${quant_script}" ]; then
    log_err "Quantization script not found: ${quant_script}"
    return 1
  fi
  
  # Prepare output directory
  rm -rf "${output_dir}"
  mkdir -p "${output_dir}"
  
  # Build quantization command
  local quant_cmd=(
    python "${quant_script}"
    --model_dir "${local_model_dir}"
    --output_dir "${output_dir}"
    --dtype "${TRT_DTYPE:-float16}"
    --qformat "${qformat}"
    --calib_size "${TRT_CALIB_SIZE:-256}"
    --batch_size "${TRT_CALIB_BATCH_SIZE:-16}"
  )
  
  # Add format-specific options
  case "${qformat}" in
    int4_awq)
      quant_cmd+=(--awq_block_size "${TRT_AWQ_BLOCK_SIZE:-128}")
      quant_cmd+=(--kv_cache_dtype int8)
      ;;
    fp8)
      quant_cmd+=(--kv_cache_dtype fp8)
      ;;
    int8_sq)
      quant_cmd+=(--kv_cache_dtype int8)
      ;;
  esac
  
  log_info "Running: ${quant_cmd[*]}"
  "${quant_cmd[@]}" || {
    log_err "Quantization failed"
    return 1
  }
  
  # Validate output
  if [ ! -f "${output_dir}/config.json" ]; then
    log_err "Quantization completed but config.json not found in output"
    return 1
  fi
  
  log_info "✓ Quantization complete: ${output_dir}"
  return 0
}

# =============================================================================
# PRE-QUANTIZED MODEL HANDLING
# =============================================================================

# Download pre-quantized TRT checkpoint from HuggingFace
trt_download_prequantized() {
  local model_id="${1:-}"
  local target_dir="${2:-}"
  
  if [ -z "${model_id}" ]; then
    log_err "Model ID is required"
    return 1
  fi
  
  if [ -z "${target_dir}" ]; then
    local model_name
    model_name=$(basename "${model_id}")
    target_dir="${TRT_CACHE_DIR:-${ROOT_DIR:-.}/.trt_cache}/${model_name}"
  fi
  
  log_info "Downloading pre-quantized TRT model: ${model_id}"
  
  # Download checkpoint files
  export HF_HUB_ENABLE_HF_TRANSFER=1
  python -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='${model_id}',
    local_dir='${target_dir}',
    local_dir_use_symlinks=False,
    allow_patterns=['trt-llm/checkpoints/**', '*.json', '*.safetensors']
)
print('✓ Downloaded pre-quantized checkpoint')
" || {
    log_err "Failed to download pre-quantized model"
    return 1
  }
  
  # Check for checkpoint directory
  local ckpt_dir="${target_dir}/trt-llm/checkpoints"
  if [ -d "${ckpt_dir}" ] && [ -f "${ckpt_dir}/config.json" ]; then
    echo "${ckpt_dir}"
  else
    echo "${target_dir}"
  fi
}

# =============================================================================
# CHECKPOINT VALIDATION
# =============================================================================

# Validate TRT-LLM checkpoint directory
trt_validate_checkpoint() {
  local ckpt_dir="${1:-}"
  
  if [ -z "${ckpt_dir}" ]; then
    log_err "Checkpoint directory is required"
    return 1
  fi
  
  if [ ! -d "${ckpt_dir}" ]; then
    log_err "Checkpoint directory not found: ${ckpt_dir}"
    return 1
  fi
  
  if [ ! -f "${ckpt_dir}/config.json" ]; then
    log_err "Checkpoint config.json not found: ${ckpt_dir}/config.json"
    return 1
  fi
  
  # Check for safetensors files
  local safetensor_count
  safetensor_count=$(find "${ckpt_dir}" -maxdepth 1 -name "*.safetensors" 2>/dev/null | wc -l)
  if [ "${safetensor_count}" -eq 0 ]; then
    log_warn "No .safetensors files found in checkpoint directory"
  else
    log_info "Found ${safetensor_count} .safetensors files"
  fi
  
  log_info "✓ Checkpoint validated: ${ckpt_dir}"
  return 0
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Get default checkpoint directory for a model
trt_get_checkpoint_dir() {
  local model_id="${1:-}"
  local qformat="${2:-int4_awq}"
  
  local model_name
  model_name=$(basename "${model_id}" | tr '[:upper:]' '[:lower:]' | tr '/' '-')
  
  echo "${TRT_CACHE_DIR:-${ROOT_DIR:-.}/.trt_cache}/${model_name}-${qformat}-ckpt"
}

# Get default engine directory for a model
trt_get_engine_dir() {
  local model_id="${1:-}"
  local qformat="${2:-int4_awq}"
  
  local model_name
  model_name=$(basename "${model_id}" | tr '[:upper:]' '[:lower:]' | tr '/' '-')
  
  echo "${TRT_MODELS_DIR:-${ROOT_DIR:-.}/models}/${model_name}-trt-${qformat}"
}

