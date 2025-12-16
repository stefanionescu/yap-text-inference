#!/usr/bin/env bash
# =============================================================================
# Centralized Environment Configuration for Yap Orpheus TTS API
# =============================================================================
# This file contains all environment variables and their defaults.
# Source this file from scripts to ensure consistent configuration.

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================

# FastAPI server settings
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8000}
# Unified API key: use ORPHEUS_API_KEY only, with default
export ORPHEUS_API_KEY=${ORPHEUS_API_KEY:?Set ORPHEUS_API_KEY in your environment}

# Model selection and authentication
# Prefer explicit MODEL_ID; otherwise derive from MODEL_PRESET (canopy|fast)
export MODEL_PRESET=${MODEL_PRESET:-canopy}
if [[ -z ${MODEL_ID:-} ]]; then
  case "${MODEL_PRESET}" in
    fast) export MODEL_ID="yapwithai/fast-orpheus-3b-0.1-ft" ;;
    canopy | *) export MODEL_ID="yapwithai/canopy-orpheus-3b-0.1-ft" ;;
  esac
fi
export ORPHEUS_PRECISION_MODE=${ORPHEUS_PRECISION_MODE:-quantized}
export HF_TOKEN=${HF_TOKEN:-} # Required: Set your Hugging Face token
export HUGGINGFACE_HUB_TOKEN=${HUGGINGFACE_HUB_TOKEN:-$HF_TOKEN}

# =============================================================================
# TENSORRT-LLM ENGINE CONFIGURATION
# =============================================================================

# Backend selection
export BACKEND=${BACKEND:-trtllm}

# Engine paths
if [[ -z ${CHECKPOINT_DIR:-} ]]; then
  if [[ ${ORPHEUS_PRECISION_MODE} == "base" ]]; then
    export CHECKPOINT_DIR="/opt/checkpoints/orpheus-trtllm-ckpt-base"
  else
    export CHECKPOINT_DIR="/opt/checkpoints/orpheus-trtllm-ckpt-int4-awq"
  fi
else
  export CHECKPOINT_DIR
fi

if [[ -z ${TRTLLM_ENGINE_DIR:-} ]]; then
  if [[ ${ORPHEUS_PRECISION_MODE} == "base" ]]; then
    export TRTLLM_ENGINE_DIR="/opt/engines/orpheus-trt-base"
  else
    export TRTLLM_ENGINE_DIR="/opt/engines/orpheus-trt-awq"
  fi
else
  export TRTLLM_ENGINE_DIR
fi

export TLLM_LOG_LEVEL=${TLLM_LOG_LEVEL:-INFO}

# TensorRT-LLM repository (using NVIDIA official repo for compatibility)
export TRTLLM_REPO_URL=${TRTLLM_REPO_URL:-https://github.com/Yap-With-AI/TensorRT-LLM.git}
export TRTLLM_CONVERT_SCRIPT=${TRTLLM_CONVERT_SCRIPT:-}

# Engine build parameters - optimized for TTS workload
if [[ -z ${TRTLLM_DTYPE+x} ]]; then
  export TRTLLM_DTYPE="float16"
  export ORPHEUS_TRTLLM_DTYPE_DEFAULTED=1
else
  export ORPHEUS_TRTLLM_DTYPE_DEFAULTED=${ORPHEUS_TRTLLM_DTYPE_DEFAULTED:-0}
  export TRTLLM_DTYPE
fi
export BASE_INFERENCE_DTYPE=${BASE_INFERENCE_DTYPE:-}
export TRTLLM_MAX_INPUT_LEN=${TRTLLM_MAX_INPUT_LEN:-48}     # Sentence-by-sentence TTS
export TRTLLM_MAX_OUTPUT_LEN=${TRTLLM_MAX_OUTPUT_LEN:-1162} # Audio token output
export TRTLLM_MAX_BATCH_SIZE=${TRTLLM_MAX_BATCH_SIZE:-16}   # Concurrent users

# Quantization parameters
export AWQ_BLOCK_SIZE=${AWQ_BLOCK_SIZE:-128} # AWQ block size (128 optimal for quality)
export CALIB_SIZE=${CALIB_SIZE:-256}         # Calibration dataset size

# KV cache memory management (critical for high concurrency)
export KV_FREE_GPU_FRAC=${KV_FREE_GPU_FRAC:-0.92}        # Use 92% of free GPU memory
export KV_ENABLE_BLOCK_REUSE=${KV_ENABLE_BLOCK_REUSE:-0} # Enable KV cache block reuse

# =============================================================================
# TTS SYNTHESIS CONFIGURATION
# =============================================================================

# Sampling defaults
export ORPHEUS_MAX_TOKENS=${ORPHEUS_MAX_TOKENS:-1162}  # ~14 seconds of audio
export DEFAULT_TEMPERATURE=${DEFAULT_TEMPERATURE:-0.45}
export DEFAULT_TOP_P=${DEFAULT_TOP_P:-0.95}
export DEFAULT_REPETITION_PENALTY=${DEFAULT_REPETITION_PENALTY:-1.15}

# Audio processing and streaming
export SNAC_SR=${SNAC_SR:-24000}                  # Sample rate
export TTS_DECODE_WINDOW=${TTS_DECODE_WINDOW:-28} # Streaming window size
export TTS_MAX_SEC=${TTS_MAX_SEC:-0}              # Max audio length (0=unlimited)

# SNAC decoder optimization
export SNAC_TORCH_COMPILE=${SNAC_TORCH_COMPILE:-0}       # Enable torch.compile
export SNAC_MAX_BATCH=${SNAC_MAX_BATCH:-64}              # Batch size for SNAC decoding
export SNAC_BATCH_TIMEOUT_MS=${SNAC_BATCH_TIMEOUT_MS:-2} # Batching timeout
export SNAC_GLOBAL_SYNC=${SNAC_GLOBAL_SYNC:-1}           # Global synchronization

# WebSocket protocol
export WS_END_SENTINEL=${WS_END_SENTINEL:-__END__}
export WS_CLOSE_BUSY_CODE=${WS_CLOSE_BUSY_CODE:-1013}
export WS_CLOSE_INTERNAL_CODE=${WS_CLOSE_INTERNAL_CODE:-1011}
export WS_QUEUE_MAXSIZE=${WS_QUEUE_MAXSIZE:-128}
export WS_MAX_CONNECTIONS=${WS_MAX_CONNECTIONS:-15}
export DEFAULT_VOICE=${DEFAULT_VOICE:-tara}

# Event loop tuning
export YIELD_SLEEP_SECONDS=${YIELD_SLEEP_SECONDS:-0}

# =============================================================================
# PERFORMANCE OPTIMIZATION
# =============================================================================

# CUDA runtime optimization
export CUDA_DEVICE_MAX_CONNECTIONS=${CUDA_DEVICE_MAX_CONNECTIONS:-2}

# PyTorch memory management
export PYTORCH_ALLOC_CONF=${PYTORCH_ALLOC_CONF:-expandable_segments:True,garbage_collection_threshold:0.9,max_split_size_mb:512}

# CPU threading (limit to prevent oversubscription)
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}
export NUMEXPR_NUM_THREADS=${NUMEXPR_NUM_THREADS:-1}

# HuggingFace optimization
export HF_TRANSFER=${HF_TRANSFER:-1} # Use hf_transfer for faster downloads

# GPU Architecture (only required for HuggingFace push)
export GPU_SM_ARCH=${GPU_SM_ARCH:-} # A100: "sm80", RTX 4090: "sm89", H100: "sm90"
# Only required when HF_PUSH_AFTER_BUILD=1 - pipeline will abort if empty during HF push

# Development and debugging toggles
export TORCH_COMPILE_DISABLE=${TORCH_COMPILE_DISABLE:-1} # Disable torch.compile by default
export TRITON_DISABLE_COMPILATION=${TRITON_DISABLE_COMPILATION:-0}

# =============================================================================
# HUGGING FACE PUBLISHING (OPTIONAL - REQUIRES GPU_SM_ARCH TO BE SET)
# =============================================================================

# Toggle push of artifacts to Hugging Face after build (0/1)
# WARNING: Pipeline will abort if GPU_SM_ARCH is empty when push is enabled
export HF_PUSH_AFTER_BUILD=${HF_PUSH_AFTER_BUILD:-0}

# Target HF repo ID (e.g., your-org/my-model-trtllm)
export HF_PUSH_REPO_ID=${HF_PUSH_REPO_ID:-}

# Private repo by default (1=private, 0=public)
export HF_PUSH_PRIVATE=${HF_PUSH_PRIVATE:-1}

# What to include: engines, checkpoints, or both
export HF_PUSH_WHAT=${HF_PUSH_WHAT:-both}

# Optional override for engine folder label (e.g., sm80_trt-llm-1.2.0rc4_cuda13.0)
export HF_PUSH_ENGINE_LABEL=${HF_PUSH_ENGINE_LABEL:-}

# Optional push behavior toggles
export HF_PUSH_PRUNE=${HF_PUSH_PRUNE:-0}         # 1=delete matching remote paths before upload
export HF_PUSH_NO_README=${HF_PUSH_NO_README:-0} # 1=do not generate README.md

# Optional: annotate build environment (e.g., container image tag)
export BUILD_IMAGE=${BUILD_IMAGE:-}

# =============================================================================
# STREAMING CONFIGURATION
# =============================================================================

# TRT-LLM streaming parameters
export STREAMING_DEFAULT_MAX_TOKENS=${STREAMING_DEFAULT_MAX_TOKENS:-1162}

# Audio token processing
export CODE_OFFSET=${CODE_OFFSET:-128266}        # First audio code ID
export CODE_SIZE=${CODE_SIZE:-4096}              # Codes per sub-stream
export FRAME_SUBSTREAMS=${FRAME_SUBSTREAMS:-7}   # Sub-streams per frame
export MIN_WINDOW_FRAMES=${MIN_WINDOW_FRAMES:-4} # Minimum window size

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Function to validate required environment variables
validate_required_env() {
  local missing_vars=()

  if [[ -z $HF_TOKEN ]]; then
    missing_vars+=("HF_TOKEN")
  fi

  if [[ -z $TRTLLM_ENGINE_DIR ]]; then
    missing_vars+=("TRTLLM_ENGINE_DIR")
  fi

  if [[ ${#missing_vars[@]} -gt 0 ]]; then
    echo "Error: Missing required environment variables:"
    printf "  - %s\n" "${missing_vars[@]}"
    echo ""
    echo "Please set these variables before running the server."
    return 1
  fi

  return 0
}

# Function to display current configuration
show_config() {
  echo "=== Yap Orpheus TTS Configuration ==="
  echo "Server: ${HOST}:${PORT}"
  echo "Model: ${MODEL_ID}"
  echo "Engine: ${TRTLLM_ENGINE_DIR}"
  echo "Max Batch: ${TRTLLM_MAX_BATCH_SIZE}"
  echo "KV Cache: ${KV_FREE_GPU_FRAC} of free GPU memory"
  echo "SNAC Batch: ${SNAC_MAX_BATCH}"
  echo "===================================="
}
