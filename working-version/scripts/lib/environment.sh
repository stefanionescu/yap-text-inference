#!/usr/bin/env bash
# =============================================================================
# Centralized Environment Configuration for Yap Orpheus TTS API
# =============================================================================
# This file contains all environment variables and their defaults.
# Source this file from scripts to ensure consistent configuration.

# Base paths (can be overridden by callers before sourcing this file)
export ORPHEUS_ENV_ROOT=${ORPHEUS_ENV_ROOT:-$PWD}
export ORPHEUS_MODELS_DIR_DEFAULT=${ORPHEUS_MODELS_DIR_DEFAULT:-${ORPHEUS_ENV_ROOT}/models}
export ORPHEUS_ENGINES_DIR_DEFAULT=${ORPHEUS_ENGINES_DIR_DEFAULT:-${ORPHEUS_MODELS_DIR_DEFAULT}}
export ORPHEUS_CHECKPOINT_BASE_DEFAULT=${ORPHEUS_CHECKPOINT_BASE_DEFAULT:-${ORPHEUS_MODELS_DIR_DEFAULT}/orpheus-trtllm-ckpt-8bit}
export ORPHEUS_CHECKPOINT_QUANT_DEFAULT=${ORPHEUS_CHECKPOINT_QUANT_DEFAULT:-${ORPHEUS_MODELS_DIR_DEFAULT}/orpheus-trtllm-ckpt-int4-awq}
export ORPHEUS_ENGINE_BASE_DEFAULT=${ORPHEUS_ENGINE_BASE_DEFAULT:-${ORPHEUS_MODELS_DIR_DEFAULT}/orpheus-trt-8bit}
export ORPHEUS_ENGINE_QUANT_DEFAULT=${ORPHEUS_ENGINE_QUANT_DEFAULT:-${ORPHEUS_MODELS_DIR_DEFAULT}/orpheus-trt-awq}
export ORPHEUS_TRTLLM_REPO_DEFAULT=${ORPHEUS_TRTLLM_REPO_DEFAULT:-${ORPHEUS_ENV_ROOT}/.trtllm-repo}
export ORPHEUS_HF_DEPLOY_WORKDIR_DEFAULT=${ORPHEUS_HF_DEPLOY_WORKDIR_DEFAULT:-${ORPHEUS_MODELS_DIR_DEFAULT}/_hf_download}
export MODELS_DIR=${MODELS_DIR:-${ORPHEUS_MODELS_DIR_DEFAULT}}
export ENGINES_DIR=${ENGINES_DIR:-${ORPHEUS_ENGINES_DIR_DEFAULT}}

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================

# FastAPI server settings
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8000}
# Unified API key: use ORPHEUS_API_KEY only, with default
export ORPHEUS_API_KEY=${ORPHEUS_API_KEY:?Set ORPHEUS_API_KEY in your environment}

# Model selection, precision, and authentication
# Prefer explicit MODEL_ID; otherwise derive from MODEL_PRESET (canopy|fast)
export MODEL_PRESET=${MODEL_PRESET:-canopy}
if [[ -z ${MODEL_ID:-} ]]; then
  case "${MODEL_PRESET}" in
    fast) export MODEL_ID="yapwithai/fast-orpheus-3b-0.1-ft" ;;
    canopy | *) export MODEL_ID="yapwithai/canopy-orpheus-3b-0.1-ft" ;;
  esac
fi
export ORPHEUS_PRECISION_MODE=${ORPHEUS_PRECISION_MODE:-quantized} # quantized|base
export HF_TOKEN=${HF_TOKEN:-}                                      # Required: Set your Hugging Face token

# =============================================================================
# TENSORRT-LLM ENGINE CONFIGURATION
# =============================================================================

# Backend selection
export BACKEND=${BACKEND:-trtllm}

if [[ -z ${CHECKPOINT_DIR:-} ]]; then
  if [[ ${ORPHEUS_PRECISION_MODE} == "base" ]]; then
    export CHECKPOINT_DIR="${ORPHEUS_CHECKPOINT_BASE_DEFAULT}"
  else
    export CHECKPOINT_DIR="${ORPHEUS_CHECKPOINT_QUANT_DEFAULT}"
  fi
else
  export CHECKPOINT_DIR
fi

if [[ -z ${TRTLLM_ENGINE_DIR:-} ]]; then
  if [[ ${ORPHEUS_PRECISION_MODE} == "base" ]]; then
    export TRTLLM_ENGINE_DIR="${ORPHEUS_ENGINE_BASE_DEFAULT}"
  else
    export TRTLLM_ENGINE_DIR="${ORPHEUS_ENGINE_QUANT_DEFAULT}"
  fi
else
  export TRTLLM_ENGINE_DIR
fi

# =============================================================================
# PYTHON AND DEPENDENCY VERSIONS
# =============================================================================
# Centralized version pins - used by bootstrap.sh, install_dependencies.sh, deps.sh

# Python version
export PYTHON_VERSION=${PYTHON_VERSION:-3.10}

# PyTorch versions (TRT-LLM 1.2.0rc5 requires torch==2.9.0 with CUDA 13.0)
export PYTORCH_VERSION=${PYTORCH_VERSION:-2.9.0+cu130}
export TORCHVISION_VERSION=${TORCHVISION_VERSION:-0.24.0+cu130}
export PYTORCH_INDEX_URL=${PYTORCH_INDEX_URL:-https://download.pytorch.org/whl/cu130}

# TensorRT-LLM version
export TRTLLM_PIP_SPEC=${TRTLLM_PIP_SPEC:-tensorrt_llm==1.2.0rc5}
export TRTLLM_EXTRA_INDEX_URL=${TRTLLM_EXTRA_INDEX_URL:-https://pypi.nvidia.com}
export TRTLLM_WHEEL_URL=${TRTLLM_WHEEL_URL:-}
export TENSORRT_PIP_EXTRAS=${TENSORRT_PIP_EXTRAS:-}

# Engine paths and runtime
export TLLM_LOG_LEVEL=${TLLM_LOG_LEVEL:-INFO}

export TRTLLM_REPO_DIR=${TRTLLM_REPO_DIR:-${ORPHEUS_TRTLLM_REPO_DEFAULT}}
# TensorRT-LLM repository (using NVIDIA official repo for compatibility)
export TRTLLM_REPO_URL=${TRTLLM_REPO_URL:-https://github.com/Yap-With-AI/TensorRT-LLM.git}
export TRTLLM_CONVERT_SCRIPT=${TRTLLM_CONVERT_SCRIPT:-}
export TRTLLM_REPO_RESET=${TRTLLM_REPO_RESET:-0}

# Engine build parameters - optimized for TTS workload
export TRTLLM_DTYPE=${TRTLLM_DTYPE:-float16}
# 8-bit quantization format is auto-detected based on GPU capability
# (FP8 for Ada/Hopper, full precision for Ampere) - no user override needed
export TRTLLM_MAX_INPUT_LEN=${TRTLLM_MAX_INPUT_LEN:-60}     # Sentence-by-sentence TTS
export TRTLLM_MAX_OUTPUT_LEN=${TRTLLM_MAX_OUTPUT_LEN:-1162} # Audio token output
if [[ -z ${TRTLLM_MAX_BATCH_SIZE+x} ]]; then
  if [[ ${ORPHEUS_PRECISION_MODE} == "base" ]]; then
    export TRTLLM_MAX_BATCH_SIZE=8
  else
    export TRTLLM_MAX_BATCH_SIZE=16
  fi
else
  export TRTLLM_MAX_BATCH_SIZE
fi

# Quantization parameters
export AWQ_BLOCK_SIZE=${AWQ_BLOCK_SIZE:-128} # AWQ block size (128 optimal for quality)
export CALIB_SIZE=${CALIB_SIZE:-32}          # Calibration dataset size

# KV cache memory management (critical for high concurrency)
export KV_FREE_GPU_FRAC=${KV_FREE_GPU_FRAC:-0.92}        # Use 92% of free GPU memory
export KV_ENABLE_BLOCK_REUSE=${KV_ENABLE_BLOCK_REUSE:-0} # Enable KV cache block reuse for shared voice prefixes

# =============================================================================
# TTS SYNTHESIS CONFIGURATION
# =============================================================================

# Sampling defaults
export ORPHEUS_MAX_TOKENS=${ORPHEUS_MAX_TOKENS:-1162} # ~14 seconds of audio
export DEFAULT_TEMPERATURE=${DEFAULT_TEMPERATURE:-0.45}
export DEFAULT_TOP_P=${DEFAULT_TOP_P:-0.95}
export DEFAULT_REPETITION_PENALTY=${DEFAULT_REPETITION_PENALTY:-1.15}

# Audio processing and streaming
export SNAC_SR=${SNAC_SR:-24000}                  # Sample rate
export TTS_DECODE_WINDOW=${TTS_DECODE_WINDOW:-28} # Streaming window size
export TTS_MAX_SEC=${TTS_MAX_SEC:-0}              # Max audio length (0=unlimited)

# SNAC decoder optimization
export SNAC_TORCH_COMPILE=${SNAC_TORCH_COMPILE:-0}              # Enable torch.compile
export SNAC_MAX_BATCH=${SNAC_MAX_BATCH:-$TRTLLM_MAX_BATCH_SIZE} # Match model batch size
export SNAC_BATCH_TIMEOUT_MS=${SNAC_BATCH_TIMEOUT_MS:-2}        # Batching timeout
export SNAC_GLOBAL_SYNC=${SNAC_GLOBAL_SYNC:-1}                  # Global synchronization

# WebSocket protocol
export WS_END_SENTINEL=${WS_END_SENTINEL:-__END__}
export WS_CLOSE_BUSY_CODE=${WS_CLOSE_BUSY_CODE:-1013}
export WS_CLOSE_INTERNAL_CODE=${WS_CLOSE_INTERNAL_CODE:-1011}
export WS_QUEUE_MAXSIZE=${WS_QUEUE_MAXSIZE:-128}
if [[ -z ${WS_MAX_CONNECTIONS+x} ]]; then
  export WS_MAX_CONNECTIONS="${TRTLLM_MAX_BATCH_SIZE}"
else
  export WS_MAX_CONNECTIONS
fi
export DEFAULT_VOICE=${DEFAULT_VOICE:-tara}

# Event loop tuning
export YIELD_SLEEP_SECONDS=${YIELD_SLEEP_SECONDS:-0}

# =============================================================================
# PERFORMANCE OPTIMIZATION
# =============================================================================

# CUDA runtime optimization
export CUDA_DEVICE_MAX_CONNECTIONS=${CUDA_DEVICE_MAX_CONNECTIONS:-2}
export TLLM_DISABLE_DEEP_GEMM=${TLLM_DISABLE_DEEP_GEMM:-1}

# MPI runtime pin for TRT-LLM (runtime-only)
export MPI_VERSION_PIN=${MPI_VERSION_PIN:-4.1.6-7ubuntu2}

# PyTorch memory management
export PYTORCH_ALLOC_CONF=${PYTORCH_ALLOC_CONF:-expandable_segments:True,garbage_collection_threshold:0.9,max_split_size_mb:512}

# CPU threading (limit to prevent oversubscription)
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-1}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-1}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}
export NUMEXPR_NUM_THREADS=${NUMEXPR_NUM_THREADS:-1}

# HuggingFace optimization
export HF_TRANSFER=${HF_TRANSFER:-1} # Use hf_transfer for faster downloads

# GPU Architecture (only required for HuggingFace push with --push-quant flag)
export GPU_SM_ARCH=${GPU_SM_ARCH:-} # A100: "sm80", RTX 4090: "sm89", H100: "sm90"
# Required when using --push-quant flag - pipeline validates this upfront

# Development and debugging toggles
export TORCH_COMPILE_DISABLE=${TORCH_COMPILE_DISABLE:-1} # Disable torch.compile by default
export TRITON_DISABLE_COMPILATION=${TRITON_DISABLE_COMPILATION:-0}

# =============================================================================
# HUGGING FACE PUBLISHING (OPTIONAL - USE --push-quant FLAG)
# =============================================================================
# HF uploads ONLY happen when you pass --push-quant to scripts/main.sh or
# scripts/restart.sh. No flag, no upload—environment variables alone will
# never trigger a push. This is intentional to prevent accidental uploads.
#
# When --push-quant is specified, the script validates these at the very
# beginning (before any downloads or heavy operations):
#   - HF_TOKEN (or HUGGINGFACE_HUB_TOKEN) with write access
#   - HF_PUSH_REPO_ID (required)
#   - GPU_SM_ARCH (required)

# Target HF repo ID (e.g., your-org/my-model-trtllm)
# Required when using --push-quant
export HF_PUSH_REPO_ID=${HF_PUSH_REPO_ID:-}

# Private repo by default (1=private, 0=public)
export HF_PUSH_PRIVATE=${HF_PUSH_PRIVATE:-1}

# What to include: engines, checkpoints, or both
export HF_PUSH_WHAT=${HF_PUSH_WHAT:-both}

# Optional override for engine folder label (e.g., sm80_trt-llm-1.2.0rc5_cuda13.0)
export HF_PUSH_ENGINE_LABEL=${HF_PUSH_ENGINE_LABEL:-}

# Optional push behavior toggles
export HF_PUSH_PRUNE=${HF_PUSH_PRUNE:-0}         # 1=delete matching remote paths before upload
export HF_PUSH_NO_README=${HF_PUSH_NO_README:-0} # 1=do not generate README.md

# Optional: annotate build environment (e.g., container image tag)
export BUILD_IMAGE=${BUILD_IMAGE:-}

# =============================================================================
# HUGGING FACE REMOTE DEPLOY (PULL) - OPTIONAL
# =============================================================================

# If set, the build step will attempt to pull a prebuilt artifact from
# this Hugging Face repo instead of quantizing locally.
# Supported content in the repo (by convention from push_to_hf.py):
#   trt-llm/checkpoints/**           (portable; requires local engine build)
#   trt-llm/engines/<label>/**      (non-portable; may allow skipping build)
export HF_DEPLOY_REPO_ID=${HF_DEPLOY_REPO_ID:-}

# What to pull if both are present in the repo.
#   auto         → prefer engines if compatible, otherwise fall back to checkpoints
#   engines      → require engines to be present; fail if not found
#   checkpoints  → require checkpoints; skip quantization and only build engine locally
export HF_DEPLOY_USE=${HF_DEPLOY_USE:-auto}

# For engines layout, choose which engines subtree to use (folder name under engines/)
# If empty, auto-select when a single label is present; otherwise attempt to match GPU_SM_ARCH.
export HF_DEPLOY_ENGINE_LABEL=${HF_DEPLOY_ENGINE_LABEL:-}

# Whether to skip local engine build when engines are downloaded successfully
export HF_DEPLOY_SKIP_BUILD_IF_ENGINES=${HF_DEPLOY_SKIP_BUILD_IF_ENGINES:-1}

# Enforce environment compatibility when using prebuilt engines (SM arch, optional TRT/CUDA)
export HF_DEPLOY_STRICT_ENV_MATCH=${HF_DEPLOY_STRICT_ENV_MATCH:-1}

# Working directory to place downloaded artifacts
export HF_DEPLOY_WORKDIR=${HF_DEPLOY_WORKDIR:-${ORPHEUS_HF_DEPLOY_WORKDIR_DEFAULT}}

# Enable integrity validation of downloaded artifacts (presence + size checks)
export HF_DEPLOY_VALIDATE=${HF_DEPLOY_VALIDATE:-1}

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

  if [[ -z $ORPHEUS_API_KEY ]]; then
    missing_vars+=("ORPHEUS_API_KEY")
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
  echo ""
  echo "[config] Server: ${HOST}:${PORT}"
  echo "[config] Model: ${MODEL_ID}"
  echo "[config] Engine: ${TRTLLM_ENGINE_DIR}"
  echo "[config] Max Batch: ${TRTLLM_MAX_BATCH_SIZE}"
  echo "[config] KV Cache: ${KV_FREE_GPU_FRAC} of free GPU memory"
  echo "[config] SNAC Batch: ${SNAC_MAX_BATCH}"
  echo ""
}
