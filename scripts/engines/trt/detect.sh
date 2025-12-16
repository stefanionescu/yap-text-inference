#!/usr/bin/env bash
# =============================================================================
# TRT-LLM Detection Utilities
# =============================================================================
# GPU architecture detection, MoE model detection, and TRT pre-quantized model detection.

# =============================================================================
# GPU ARCHITECTURE DETECTION
# =============================================================================

# Detect GPU SM architecture from nvidia-smi
# Returns: sm80 (A100), sm89 (L40S), sm90 (H100), etc.
trt_detect_gpu_sm_arch() {
  if [ -n "${GPU_SM_ARCH:-}" ]; then
    echo "${GPU_SM_ARCH}"
    return 0
  fi
  
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    log_warn "nvidia-smi not found, cannot detect GPU architecture"
    echo ""
    return 1
  fi
  
  # Get GPU name and map to SM architecture
  local gpu_name
  gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 | tr '[:upper:]' '[:lower:]')
  
  if [ -z "${gpu_name}" ]; then
    log_warn "Could not detect GPU name"
    echo ""
    return 1
  fi
  
  # Map GPU name to SM architecture
  local sm_arch=""
  case "${gpu_name}" in
    *"h100"*)
      sm_arch="sm90"
      ;;
    *"l40s"* | *"l40"* | *"rtx 4090"* | *"rtx 4080"* | *"rtx 4070"* | *"ada"*)
      sm_arch="sm89"
      ;;
    *"a100"* | *"a10"* | *"a30"* | *"rtx 3090"* | *"rtx 3080"* | *"ampere"*)
      sm_arch="sm80"
      ;;
    *"v100"* | *"volta"*)
      sm_arch="sm70"
      ;;
    *)
      # Try to get compute capability directly
      local compute_cap
      compute_cap=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -n1 | tr -d '.')
      if [ -n "${compute_cap}" ]; then
        sm_arch="sm${compute_cap}"
      else
        log_warn "Unknown GPU: ${gpu_name}, defaulting to sm89 (L40S)"
        sm_arch="sm89"
      fi
      ;;
  esac
  
  echo "${sm_arch}"
}

# Get human-readable GPU name
trt_get_gpu_name() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "Unknown"
    return
  fi
  nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -n1 || echo "Unknown"
}

# Get GPU VRAM in GB
trt_get_gpu_vram_gb() {
  if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "0"
    return
  fi
  local vram_mb
  vram_mb=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -n1)
  if [ -n "${vram_mb}" ]; then
    echo $((vram_mb / 1024))
  else
    echo "0"
  fi
}

# =============================================================================
# MOE MODEL DETECTION
# =============================================================================

# Check if model is a Mixture of Experts (MoE) model
# MoE models require quantize_mixed_precision_moe.py instead of quantize.py
trt_is_moe_model() {
  local model="${1:-}"
  if [ -z "${model}" ]; then
    return 1
  fi
  
  local lowered
  lowered=$(echo "${model}" | tr '[:upper:]' '[:lower:]')
  
  # Check for Qwen3 MoE naming convention: -aXb suffix (e.g., qwen3-30b-a3b)
  if echo "${lowered}" | grep -qE -- '-a[0-9]+b'; then
    return 0
  fi
  
  # Check for common MoE markers
  local moe_markers="moe mixtral deepseek-v2 deepseek-v3 ernie-4.5"
  local marker
  for marker in ${moe_markers}; do
    if echo "${lowered}" | grep -q "${marker}"; then
      return 0
    fi
  done
  
  return 1
}

# Get the appropriate quantization script for a model
trt_get_quantize_script() {
  local model="${1:-}"
  local trtllm_repo="${2:-${TRT_REPO_DIR}}"
  
  local base_script="${trtllm_repo}/examples/quantization/quantize.py"
  local moe_script="${trtllm_repo}/examples/quantization/quantize_mixed_precision_moe.py"
  
  if trt_is_moe_model "${model}"; then
    if [ -f "${moe_script}" ]; then
      echo "${moe_script}"
    else
      log_warn "MoE quantize script not found: ${moe_script}, falling back to base script"
      echo "${base_script}"
    fi
  else
    echo "${base_script}"
  fi
}

# =============================================================================
# TRT PRE-QUANTIZED MODEL DETECTION
# =============================================================================

# Check if model is a TRT pre-quantized model (contains both 'trt' and 'awq')
trt_is_prequantized_model() {
  local model="${1:-}"
  if [ -z "${model}" ]; then
    return 1
  fi
  
  local lowered
  lowered=$(echo "${model}" | tr '[:upper:]' '[:lower:]')
  
  # Must contain both 'trt' and 'awq'
  if echo "${lowered}" | grep -q "trt" && echo "${lowered}" | grep -q "awq"; then
    return 0
  fi
  
  return 1
}

# =============================================================================
# CUDA VERSION DETECTION
# =============================================================================

# Detect CUDA toolkit version
trt_detect_cuda_version() {
  # 1. Check CUDA_VERSION env var (common in containers)
  if [ -n "${CUDA_VERSION:-}" ]; then
    echo "${CUDA_VERSION}" | grep -oE '^[0-9]+\.[0-9]+' 2>/dev/null || echo "${CUDA_VERSION}"
    return
  fi
  
  # 2. Check nvcc (actual toolkit version)
  if command -v nvcc >/dev/null 2>&1; then
    nvcc --version 2>/dev/null | grep -oE 'release [0-9]+\.[0-9]+' | awk '{print $2}' 2>/dev/null && return
  fi
  
  # 3. Fallback to nvidia-smi
  if command -v nvidia-smi >/dev/null 2>&1; then
    timeout 10s nvidia-smi 2>/dev/null | grep -o "CUDA Version: [0-9][0-9]*\.[0-9]*" | awk '{print $3}' 2>/dev/null || echo ""
  else
    echo ""
  fi
}

# Check if CUDA version is compatible with TRT-LLM 1.2.0rc4 (requires CUDA 13.0)
trt_check_cuda_compatibility() {
  local cuda_ver
  cuda_ver=$(trt_detect_cuda_version)
  
  if [ -z "${cuda_ver}" ]; then
    log_warn "Could not detect CUDA version"
    return 1
  fi
  
  local major
  major=$(echo "${cuda_ver}" | cut -d. -f1)
  
  if [ "${major}" -lt 13 ]; then
    log_warn "TRT-LLM 1.2.0rc4 requires CUDA 13.0+, found ${cuda_ver}"
    return 1
  fi
  
  return 0
}

# =============================================================================
# INITIALIZATION
# =============================================================================

# Auto-detect GPU SM arch if not set
trt_init_gpu_detection() {
  if [ -z "${GPU_SM_ARCH:-}" ]; then
    GPU_SM_ARCH=$(trt_detect_gpu_sm_arch)
    export GPU_SM_ARCH
    if [ -n "${GPU_SM_ARCH}" ]; then
      log_info "Detected GPU architecture: ${GPU_SM_ARCH} ($(trt_get_gpu_name))"
    fi
  fi
}

