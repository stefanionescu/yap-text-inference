#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Engine Build Utilities
# =============================================================================
# Functions for building TensorRT-LLM engines from quantized checkpoints.

# =============================================================================
# ENGINE BUILD
# =============================================================================

# Build TensorRT-LLM engine from checkpoint
# Usage: trt_build_engine <checkpoint_dir> <engine_dir> [options...]
trt_build_engine() {
  local checkpoint_dir="${1:-}"
  local engine_dir="${2:-}"
  
  if [ -z "${checkpoint_dir}" ]; then
    log_err "Checkpoint directory is required"
    return 1
  fi
  
  if [ -z "${engine_dir}" ]; then
    log_err "Engine output directory is required"
    return 1
  fi
  
  # Validate checkpoint
  trt_validate_checkpoint "${checkpoint_dir}" || return 1
  
  # Check if engine already exists
  if [ -d "${engine_dir}" ] && ls "${engine_dir}"/rank*.engine >/dev/null 2>&1; then
    if [ "${FORCE_REBUILD:-false}" != "true" ]; then
      log_info "Reusing existing engine at ${engine_dir}"
      return 0
    fi
    log_info "FORCE_REBUILD=true, rebuilding engine..."
  fi
  
  log_info "Building TensorRT-LLM engine"
  log_info "Checkpoint: ${checkpoint_dir}"
  log_info "Engine output: ${engine_dir}"
  
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
    --paged_kv_cache enable
    --remove_input_padding enable
    --max_input_len "${TRT_MAX_INPUT_LEN:-8192}"
    --max_seq_len "${max_seq_len}"
    --max_batch_size "${TRT_MAX_BATCH_SIZE:-16}"
    --log_level info
    --workers "$(nproc --all)"
  )
  
  log_info "Running: ${build_cmd[*]}"
  "${build_cmd[@]}" || {
    log_err "Engine build failed"
    return 1
  }
  
  # Validate engine was created
  if ! ls "${engine_dir}"/rank*.engine >/dev/null 2>&1; then
    log_err "Engine build completed but no rank*.engine files found"
    return 1
  fi
  
  # Record build metadata
  trt_record_build_metadata "${engine_dir}" "${checkpoint_dir}"
  
  log_info "✓ Engine build complete: ${engine_dir}"
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
  --paged_kv_cache enable \\
  --remove_input_padding enable \\
  --max_input_len ${TRT_MAX_INPUT_LEN:-8192} \\
  --max_seq_len $((TRT_MAX_INPUT_LEN + TRT_MAX_OUTPUT_LEN)) \\
  --max_batch_size ${TRT_MAX_BATCH_SIZE:-16} \\
  --log_level info
EOF
  chmod +x "${cmd_file}"
  
  # Get TensorRT-LLM version
  local trtllm_ver
  trtllm_ver=$(python -c "import tensorrt_llm; print(tensorrt_llm.__version__)" 2>/dev/null || echo "unknown")
  
  # Get CUDA version
  local cuda_ver
  cuda_ver=$(trt_detect_cuda_version 2>/dev/null || echo "unknown")
  
  # Get GPU info
  local gpu_name
  gpu_name=$(trt_get_gpu_name 2>/dev/null || echo "unknown")
  
  local gpu_vram
  gpu_vram=$(trt_get_gpu_vram_gb 2>/dev/null || echo "0")
  
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
  
  # Write metadata
  local meta_file="${engine_dir}/build_metadata.json"
  cat >"${meta_file}" <<EOF
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
  "built_at": "$(date -Iseconds)"
}
EOF
  
  log_info "Build metadata recorded to ${meta_file}"
}

# =============================================================================
# ENGINE VALIDATION
# =============================================================================

# Validate TensorRT-LLM engine directory
trt_validate_engine() {
  local engine_dir="${1:-${TRT_ENGINE_DIR:-}}"
  
  if [ -z "${engine_dir}" ]; then
    log_err "Engine directory is required"
    return 1
  fi
  
  if [ ! -d "${engine_dir}" ]; then
    log_err "Engine directory not found: ${engine_dir}"
    return 1
  fi
  
  # Check for engine files
  if ! ls "${engine_dir}"/rank*.engine >/dev/null 2>&1; then
    log_err "No rank*.engine files found in ${engine_dir}"
    return 1
  fi
  
  local engine_count
  engine_count=$(ls "${engine_dir}"/rank*.engine 2>/dev/null | wc -l)
  log_info "Found ${engine_count} engine file(s)"
  
  # Check for metadata
  if [ ! -f "${engine_dir}/build_metadata.json" ]; then
    log_warn "build_metadata.json not found (non-critical)"
  fi
  
  log_info "✓ Engine validated: ${engine_dir}"
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
    log_err "Model ID is required"
    return 1
  fi
  
  # Resolve qformat
  if [ -z "${qformat}" ]; then
    qformat=$(trt_resolve_qformat "${QUANTIZATION:-4bit}" "${GPU_SM_ARCH:-}")
  fi
  
  log_info "Starting TRT quantize and build pipeline"
  log_info "Model: ${model_id}"
  log_info "Format: ${qformat}"
  log_info "GPU: ${GPU_SM_ARCH:-auto} ($(trt_get_gpu_name))"
  
  # Check if this is a pre-quantized model
  if trt_is_prequantized_model "${model_id}"; then
    log_info "Detected pre-quantized TRT model"
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
  
  log_info "✓ Quantize and build pipeline complete"
  log_info "Engine directory: ${TRT_ENGINE_DIR}"
  
  return 0
}

# =============================================================================
# HUGGING FACE PUSH
# =============================================================================

# Push quantized model to HuggingFace
trt_push_to_hf() {
  local checkpoint_dir="${1:-${TRT_CHECKPOINT_DIR:-}}"
  local engine_dir="${2:-${TRT_ENGINE_DIR:-}}"
  local repo_id="${3:-${TRT_HF_PUSH_REPO_ID:-}}"
  local base_model="${4:-${CHAT_MODEL:-}}"
  local quant_method="${5:-${TRT_QUANT_METHOD:-int4_awq}}"
  
  if [ "${TRT_HF_PUSH_ENABLED:-0}" != "1" ] && [ "${HF_AWQ_PUSH:-0}" != "1" ]; then
    log_info "HF push not enabled (TRT_HF_PUSH_ENABLED=0)"
    return 0
  fi
  
  if [ -z "${repo_id}" ]; then
    log_warn "No HF repo ID specified, skipping push"
    return 0
  fi
  
  if [ ! -d "${checkpoint_dir}" ]; then
    log_warn "Checkpoint directory not found: ${checkpoint_dir}"
    return 1
  fi
  
  local token="${HF_TOKEN:-}"
  if [ -z "${token}" ]; then
    log_warn "HF_TOKEN not set, skipping push"
    return 1
  fi
  
  log_info "Pushing TRT-LLM model to HuggingFace: ${repo_id}"
  
  local python_cmd=(
    "${ROOT_DIR}/.venv/bin/python"
    "-m" "src.engines.trt.hf.hf_push"
    "--checkpoint-dir" "${checkpoint_dir}"
    "--repo-id" "${repo_id}"
    "--token" "${token}"
    "--quant-method" "${quant_method}"
  )
  
  # Add engine dir if it exists
  if [ -n "${engine_dir}" ] && [ -d "${engine_dir}" ]; then
    python_cmd+=("--engine-dir" "${engine_dir}")
  fi
  
  # Add base model if specified
  if [ -n "${base_model}" ]; then
    python_cmd+=("--base-model" "${base_model}")
  fi
  
  if "${python_cmd[@]}"; then
    log_info "Successfully pushed to HuggingFace"
    return 0
  else
    log_warn "HuggingFace push failed"
    return 1
  fi
}

