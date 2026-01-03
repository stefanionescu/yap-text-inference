#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Quantization Utilities
# =============================================================================
# Functions for quantizing models with TensorRT-LLM.

# =============================================================================
# PATH SETUP
# =============================================================================

_TRT_QUANT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_TRT_QUANT_ROOT="${ROOT_DIR:-$(cd "${_TRT_QUANT_DIR}/../../.." && pwd)}"

# =============================================================================
# MODEL DOWNLOAD
# =============================================================================

# Download model from HuggingFace to local directory
trt_download_model() {
  local model_id="${1:-}"
  local target_dir="${2:-}"
  
  if [ -z "${model_id}" ]; then
    log_err "[model] ✗ Model ID is required"
    return 1
  fi
  
  # If model_id is a local path, use it directly
  if [ -d "${model_id}" ]; then
    log_info "[model] Using local model path: ${model_id}"
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
    log_info "[model] ✓ Using cached model at ${target_dir}"
    echo "${target_dir}"
    return 0
  fi
  
  log_info "[model] Downloading model from HuggingFace..."
  log_blank
  
  mkdir -p "${target_dir}"
  
  # Enable HF transfer for faster downloads
  hf_enable_transfer "[model]" "python" || true
  
  # Pass SHOW_HF_LOGS to Python so it can re-enable progress bars if user wants them
  local show_hf_logs_env=""
  if [ "${SHOW_HF_LOGS:-false}" = "true" ] || [ "${SHOW_HF_LOGS:-0}" = "1" ]; then
    show_hf_logs_env="SHOW_HF_LOGS=1"
  fi
  
  local python_root="${ROOT_DIR:-${_TRT_QUANT_ROOT}}"
  local download_start download_end download_duration
  download_start=$(date +%s)
  
  if ! env ${show_hf_logs_env} PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" python -m src.scripts.quantization download-model \
    --model-id "${model_id}" \
    --target-dir "${target_dir}"; then
    log_err "[model] ✗ Failed to download model ${model_id}"
    log_err "[model] Check network connectivity and HuggingFace authentication"
    # Cleanup partial download to avoid inconsistent state
    if [ -d "${target_dir}" ] && [ ! -f "${target_dir}/config.json" ]; then
      log_warn "[model] ⚠ Cleaning up partial download at ${target_dir}"
      rm -rf "${target_dir}"
    fi
    return 1
  fi
  
  download_end=$(date +%s)
  download_duration=$((download_end - download_start))
  log_info "[model] ✓ Download completed in ${download_duration}s"
  
  echo "${target_dir}"
}

# =============================================================================
# QUANTIZATION
# =============================================================================

# Quantize a model to TRT-LLM checkpoint format
# Usage: trt_quantize_model <model_id> <output_dir> [qformat]
# Follows the pattern from trtllm-example/custom/build/steps/step_quantize.sh
trt_quantize_model() {
  local model_id="${1:-}"
  local output_dir="${2:-}"
  local qformat="${3:-}"
  
  if [ -z "${model_id}" ]; then
    log_err "[quant] ✗ Model ID is required"
    return 1
  fi
  
  if [ -z "${output_dir}" ]; then
    log_err "[quant] ✗ Output directory is required"
    return 1
  fi
  
  # Resolve qformat if not specified (pass model_id for MoE detection)
  if [ -z "${qformat}" ]; then
    qformat=$(trt_resolve_qformat "${QUANTIZATION:-4bit}" "${GPU_SM_ARCH:-}" "${model_id}")
  fi
  
  # Check if already quantized
  if [ -d "${output_dir}" ] && [ -f "${output_dir}/config.json" ]; then
    if [ "${FORCE_REBUILD:-false}" != "true" ]; then
      log_info "[quant] Reusing existing checkpoint at ${output_dir}"
      return 0
    fi
    log_info "[quant] FORCE_REBUILD=true, re-quantizing..."
  fi
  
  # Install quantization requirements from TRT-LLM repo BEFORE quantizing
  # This follows the pattern from trtllm-example/custom/build/steps/step_quantize.sh
  trt_install_quant_requirements
  
  # Download model if needed
  local local_model_dir
  local_model_dir=$(trt_download_model "${model_id}") || return 1
  
  # Get the appropriate quantization script
  local quant_script
  quant_script=$(trt_get_quantize_script "${TRT_REPO_DIR}")
  
  if [ ! -f "${quant_script}" ]; then
    log_err "[quant] ✗ Quantization script not found: ${quant_script}"
    return 1
  fi
  
  # Prepare output directory
  rm -rf "${output_dir}"
  mkdir -p "${output_dir}"
  
  # Cleanup function for partial failures
  _quant_cleanup_on_failure() {
    log_warn "[quant] ⚠ Cleaning up partial output at ${output_dir}"
    rm -rf "${output_dir}"
  }
  
  # Build quantization command
  local quant_args=(
    "${quant_script}"
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
      quant_args+=(--awq_block_size "${TRT_AWQ_BLOCK_SIZE:-128}")
      quant_args+=(--kv_cache_dtype int8)
      ;;
    fp8)
      quant_args+=(--kv_cache_dtype fp8)
      ;;
    int8_sq)
      quant_args+=(--kv_cache_dtype int8)
      ;;
  esac
  
  # Apply transformers patch for Python 3.10 + union type compatibility
  # This patches auto_docstring to handle types.UnionType gracefully (Kimi models)
  local patch_script="${ROOT_DIR}/src/scripts/patches.py"
  if [ -f "${patch_script}" ]; then
    export TRANSFORMERS_PATCH_SCRIPT="${patch_script}"
  fi
  
  # Suppress TRT-LLM/modelopt log noise
  export TRTLLM_LOG_LEVEL="${TRTLLM_LOG_LEVEL:-error}"
  export TQDM_DISABLE="${TQDM_DISABLE:-1}"
  export HF_HUB_DISABLE_PROGRESS_BARS="${HF_HUB_DISABLE_PROGRESS_BARS:-1}"
  
  # Run with patch and log filter applied via Python helper
  local patch_args=()
  if [ -n "${patch_script}" ] && [ -f "${patch_script}" ]; then
    patch_args=(--patch-script "${patch_script}")
  fi
  local python_root="${ROOT_DIR:-${_TRT_QUANT_ROOT}}"
  if ! PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" python -m src.scripts.quantization run-quant \
    "${patch_args[@]}" -- "${quant_args[@]}"; then
    log_err "[quant] ✗ Quantization failed"
    _quant_cleanup_on_failure
    return 1
  fi
  
  # Validate output
  if [ ! -f "${output_dir}/config.json" ]; then
    log_err "[quant] ✗ Quantization completed but config.json not found in output"
    _quant_cleanup_on_failure
    return 1
  fi
  
  log_info "[quant] ✓ Quantization complete"
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
    log_err "[model] ✗ Model ID is required"
    return 1
  fi
  
  if [ -z "${target_dir}" ]; then
    local model_name
    model_name=$(basename "${model_id}")
    target_dir="${TRT_CACHE_DIR:-${ROOT_DIR:-.}/.trt_cache}/${model_name}"
  fi
  
  log_info "[model] Downloading pre-quantized TRT model..."
  # Check if already downloaded
  local ckpt_dir="${target_dir}/trt-llm/checkpoints"
  if [ -d "${ckpt_dir}" ] && [ -f "${ckpt_dir}/config.json" ]; then
    log_info "[model] ✓ Pre-quantized model checkpoint already cached locally"
    echo "${ckpt_dir}"
    return 0
  fi
  
  mkdir -p "${target_dir}"
  
  # Enable HF transfer for faster downloads
  hf_enable_transfer "[model]" "python" || true
  
  # Pass SHOW_HF_LOGS to Python so it can re-enable progress bars if user wants them
  local show_hf_logs_env=""
  if [ "${SHOW_HF_LOGS:-false}" = "true" ] || [ "${SHOW_HF_LOGS:-0}" = "1" ]; then
    show_hf_logs_env="SHOW_HF_LOGS=1"
  fi
  
  log_blank
  
  local python_root="${ROOT_DIR:-${_TRT_QUANT_ROOT}}"
  
  if ! env ${show_hf_logs_env} PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" python -m src.scripts.quantization download-prequantized \
    --model-id "${model_id}" \
    --target-dir "${target_dir}"; then
    log_err "[model] ✗ Failed to download pre-quantized model"
    log_err "[model] Check network connectivity and HuggingFace authentication"
    # Cleanup partial download to avoid inconsistent state
    if [ -d "${target_dir}" ]; then
      if [ ! -f "${ckpt_dir}/config.json" ] && [ ! -f "${target_dir}/config.json" ]; then
        log_warn "[model] ⚠ Cleaning up partial download at ${target_dir}"
        rm -rf "${target_dir}"
      fi
    fi
    return 1
  fi
  
  # Check for checkpoint directory
  if [ -d "${ckpt_dir}" ] && [ -f "${ckpt_dir}/config.json" ]; then
    echo "${ckpt_dir}"
  elif [ -f "${target_dir}/config.json" ]; then
    echo "${target_dir}"
  else
    log_err "[model] ✗ Download completed but no config.json found"
    return 1
  fi
}

# =============================================================================
# CHECKPOINT VALIDATION
# =============================================================================

# Validate TRT-LLM checkpoint directory
trt_validate_checkpoint() {
  local ckpt_dir="${1:-}"
  
  if [ -z "${ckpt_dir}" ]; then
    log_err "[quant] ✗ Checkpoint directory is required"
    return 1
  fi
  
  if [ ! -d "${ckpt_dir}" ]; then
    log_err "[quant] ✗ Checkpoint directory not found: ${ckpt_dir}"
    return 1
  fi
  
  if [ ! -f "${ckpt_dir}/config.json" ]; then
    log_err "[quant] ✗ Checkpoint config.json not found: ${ckpt_dir}/config.json"
    return 1
  fi
  
  # Check for safetensors files - these are required for the engine build
  local safetensor_count
  safetensor_count=$(find "${ckpt_dir}" -maxdepth 1 -name "*.safetensors" 2>/dev/null | wc -l)
  if [ "${safetensor_count}" -eq 0 ]; then
    log_err "[quant] ✗ No .safetensors files found in checkpoint directory"
    log_err "[quant] Expected model weights at: ${ckpt_dir}/*.safetensors"
    log_info "[quant] Directory contents:"
    find "${ckpt_dir}" -maxdepth 1 -printf '%M %u %g %s %f\n' 2>/dev/null | head -20 | while read -r line; do
      log_info "[quant]   ${line}"
    done
    return 1
  fi
  
  log_info "[quant] ✓ Checkpoint validated"
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
