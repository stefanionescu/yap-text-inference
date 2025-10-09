#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Setting AWQ Docker environment defaults"

# Validate required AWQ models are set
if [ -z "${AWQ_CHAT_MODEL:-}" ] && [ -z "${AWQ_TOOL_MODEL:-}" ]; then
  log_error "Error: At least one of AWQ_CHAT_MODEL or AWQ_TOOL_MODEL must be set for Docker deployment"
  log_error "Example: docker run -e AWQ_CHAT_MODEL=your-org/chat-awq -e AWQ_TOOL_MODEL=your-org/tool-awq ..."
  exit 1
fi

# Deploy mode: both | chat | tool (default: both)
export DEPLOY_MODELS=${DEPLOY_MODELS:-both}
case "${DEPLOY_MODELS}" in
  both|chat|tool)
    ;;
  *)
    log_warn "Invalid DEPLOY_MODELS='${DEPLOY_MODELS}', defaulting to 'both'"
    export DEPLOY_MODELS=both
    ;;
esac

# Convenience booleans for shell usage
DEPLOY_CHAT=0
DEPLOY_TOOL=0
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "chat" ]; then
  DEPLOY_CHAT=1
fi
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "tool" ]; then
  DEPLOY_TOOL=1
fi
export DEPLOY_CHAT
export DEPLOY_TOOL

# Validate AWQ models are set for deployed components
if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${AWQ_CHAT_MODEL:-}" ]; then
  log_error "Error: AWQ_CHAT_MODEL must be set when DEPLOY_MODELS='both' or 'chat'"
  exit 1
fi

if [ "${DEPLOY_TOOL}" = "1" ] && [ -z "${AWQ_TOOL_MODEL:-}" ]; then
  log_error "Error: AWQ_TOOL_MODEL must be set when DEPLOY_MODELS='both' or 'tool'"
  exit 1
fi

# Set model paths to AWQ checkpoints
if [ "${DEPLOY_CHAT}" = "1" ]; then
  export CHAT_MODEL="${AWQ_CHAT_MODEL}"
  export CHAT_QUANTIZATION=awq
fi

if [ "${DEPLOY_TOOL}" = "1" ]; then
  export TOOL_MODEL="${AWQ_TOOL_MODEL}"  
  export TOOL_QUANTIZATION=awq
fi

# Force AWQ quantization mode
export QUANTIZATION=awq

# Context and output limits
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5160}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-200}
export TOOL_MAX_OUT=${TOOL_MAX_OUT:-10}
export TOOL_MAX_LEN=${TOOL_MAX_LEN:-3000}

# GPU memory fractions (weights + KV). Use fractions only.
export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.70}
export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}

# Concurrent model calling mode: 0=sequential, 1=concurrent (default: concurrent for Docker)
export CONCURRENT_MODEL_CALL=${CONCURRENT_MODEL_CALL:-1}

# Token limits (approx)
export HISTORY_MAX_TOKENS=${HISTORY_MAX_TOKENS:-2400}
export USER_UTT_MAX_TOKENS=${USER_UTT_MAX_TOKENS:-350}
export TOOL_HISTORY_TOKENS=${TOOL_HISTORY_TOKENS:-1200}
export TOOL_SYSTEM_TOKENS=${TOOL_SYSTEM_TOKENS:-1450}

# vLLM engine selection
export VLLM_USE_V1=${VLLM_USE_V1:-1}
export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=${VLLM_ALLOW_LONG_MAX_MODEL_LEN:-1}

# GPU detection and optimization
GPU_NAME=""
if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 || true)
fi
export DETECTED_GPU_NAME="${GPU_NAME}"

# Set GPU-specific defaults based on GPU type (AWQ optimized)
case "${GPU_NAME}" in
  *H100*|*L40S*|*L40*)
    export KV_DTYPE=${KV_DTYPE:-fp8}
    export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
    export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
    export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
    export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    ;;
  *A100*)
    export VLLM_USE_V1=0
    export KV_DTYPE=${KV_DTYPE:-int8}
    export VLLM_ATTENTION_BACKEND=XFORMERS
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
    export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
    export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
    export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    export CUDA_DEVICE_MAX_CONNECTIONS=1
    ;;
  *)
    # Unknown GPU: conservative defaults
    export KV_DTYPE=${KV_DTYPE:-auto}
    export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
    ;;
esac

# Final defaults if still unset
export KV_DTYPE=${KV_DTYPE:-auto}
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}

CONCURRENT_STATUS="sequential"
if [ "${CONCURRENT_MODEL_CALL:-1}" = "1" ]; then
  CONCURRENT_STATUS="concurrent"
fi

log_info "Docker AWQ Configuration:"
log_info "  GPU: ${DETECTED_GPU_NAME:-unknown}"
log_info "  Deploy mode: ${DEPLOY_MODELS} (chat=${DEPLOY_CHAT}, tool=${DEPLOY_TOOL})"
log_info "  Chat model: ${CHAT_MODEL:-none}"
log_info "  Tool model: ${TOOL_MODEL:-none}"
log_info "  Quantization: ${QUANTIZATION}"
log_info "  KV dtype: ${KV_DTYPE}"
log_info "  Model calls: ${CONCURRENT_STATUS}"
