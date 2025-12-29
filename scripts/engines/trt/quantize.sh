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
    log_info "[model] Using cached model at ${target_dir}"
    echo "${target_dir}"
    return 0
  fi
  
  log_info "[model] Downloading model ${model_id} to ${target_dir}..."
  log_blank
  
  mkdir -p "${target_dir}"
  
  hf_enable_transfer "[model]" "python" || true
  
  local python_root="${ROOT_DIR:-${_TRT_QUANT_ROOT}}"
  if ! PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" python <<PYTHON; then
import sys
import src.scripts.site_customize as _site_customize  # noqa: F401
from huggingface_hub import snapshot_download

snapshot_download(repo_id='${model_id}', local_dir='${target_dir}')
print('✓ Downloaded model', file=sys.stderr)
PYTHON
    log_err "[model] ✗ Failed to download model ${model_id}"
    # Cleanup partial download to avoid inconsistent state
    if [ -d "${target_dir}" ] && [ ! -f "${target_dir}/config.json" ]; then
      log_warn "[model] ⚠ Cleaning up partial download at ${target_dir}"
      rm -rf "${target_dir}"
    fi
    return 1
  fi
  
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
  
  local kv_cache_dtype
  kv_cache_dtype=$(trt_resolve_kv_cache_dtype "${qformat}")
  
  log_info "[quant] Quantizing model ${model_id} to ${qformat}..."
  
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
  quant_script=$(trt_get_quantize_script "${model_id}" "${TRT_REPO_DIR}")
  
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
  
  # Apply transformers patch for Python 3.10 + union type compatibility
  # This patches auto_docstring to handle types.UnionType gracefully (Kimi models)
  local patch_script="${ROOT_DIR}/src/scripts/transformers.py"
  if [ -f "${patch_script}" ]; then
    export TRANSFORMERS_PATCH_SCRIPT="${patch_script}"
  fi
  
  # Run with patch applied via -c wrapper
  if ! python -c "
import os, sys, runpy
patch = os.environ.get('TRANSFORMERS_PATCH_SCRIPT')
if patch:
    exec(open(patch).read())
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
" "${quant_cmd[@]:1}"; then
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
  
  log_info "[model] Downloading pre-quantized TRT model: ${model_id}"
  mkdir -p "${target_dir}"
  
  hf_enable_transfer "[model]" "python" || true
  
  local python_root="${ROOT_DIR:-${_TRT_QUANT_ROOT}}"
  if ! PYTHONPATH="${python_root}${PYTHONPATH:+:${PYTHONPATH}}" python <<PYTHON; then
import sys
import src.scripts.site_customize as _site_customize  # noqa: F401
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id='${model_id}',
    local_dir='${target_dir}',
    allow_patterns=['trt-llm/checkpoints/**', '*.json', '*.safetensors']
)
print('✓ Downloaded pre-quantized checkpoint', file=sys.stderr)
PYTHON
    log_err "[model] ✗ Failed to download pre-quantized model"
    # Cleanup partial download to avoid inconsistent state
    if [ -d "${target_dir}" ]; then
      local ckpt_dir="${target_dir}/trt-llm/checkpoints"
      if [ ! -f "${ckpt_dir}/config.json" ] && [ ! -f "${target_dir}/config.json" ]; then
        log_warn "[model] ⚠ Cleaning up partial download at ${target_dir}"
        rm -rf "${target_dir}"
      fi
    fi
    return 1
  fi
  
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
  
  # Check for safetensors files
  local safetensor_count
  safetensor_count=$(find "${ckpt_dir}" -maxdepth 1 -name "*.safetensors" 2>/dev/null | wc -l)
  if [ "${safetensor_count}" -eq 0 ]; then
    log_warn "[quant] ⚠ No .safetensors files found in checkpoint directory"
  fi
  
  log_info "[quant] ✓ Checkpoint validated"
  log_blank
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
