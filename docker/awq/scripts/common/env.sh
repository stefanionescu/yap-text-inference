#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Setting environment defaults"

# Ensure QUANTIZATION is set (Docker AWQ stack defaults to 'awq')
export QUANTIZATION=${QUANTIZATION:-awq}

# Detect FlashInfer availability (optional fast-path)
HAS_FLASHINFER=0
if [ -f "/opt/venv/bin/python" ]; then
  PY_BIN="/opt/venv/bin/python"
elif [ -f "${SCRIPT_DIR}/../../.venv/bin/python" ]; then
  PY_BIN="${SCRIPT_DIR}/../../.venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PY_BIN="python"
else
  PY_BIN=""
fi

if [ -n "${PY_BIN}" ]; then
  if "${PY_BIN}" - <<'PY' >/dev/null 2>&1
try:
    import flashinfer  # noqa: F401
except Exception:
    raise SystemExit(1)
PY
  then
    HAS_FLASHINFER=1
  fi
fi
export HAS_FLASHINFER

# Set default AWQ models if not provided by user
export AWQ_CHAT_MODEL=${AWQ_CHAT_MODEL:-yapwithai/impish-12b-awq}
export AWQ_TOOL_MODEL=${AWQ_TOOL_MODEL:-yapwithai/hammer-2.1-3b-awq}

if [ -n "${AWQ_CHAT_MODEL:-}" ] || [ -n "${AWQ_TOOL_MODEL:-}" ]; then
  log_info "AWQ models configured:"
  log_info "  Chat: ${AWQ_CHAT_MODEL:-none}"
  log_info "  Tool: ${AWQ_TOOL_MODEL:-none}"
fi

# Always deploy both models in Docker
export DEPLOY_MODELS=both

# Convenience booleans (forced to both)
DEPLOY_CHAT=1
DEPLOY_TOOL=1
export DEPLOY_CHAT
export DEPLOY_TOOL

# Validate AWQ models only when QUANTIZATION=awq (require both)
if [ "${QUANTIZATION:-awq}" = "awq" ]; then
  if [ -z "${AWQ_CHAT_MODEL:-}" ]; then
    log_error "Error: AWQ_CHAT_MODEL must be set for AWQ mode"
    exit 1
  fi
  if [ -z "${AWQ_TOOL_MODEL:-}" ]; then
    log_error "Error: AWQ_TOOL_MODEL must be set for AWQ mode"
    exit 1
  fi
fi

# Set model paths to AWQ checkpoints when in AWQ mode (always both)
if [ "${QUANTIZATION:-awq}" = "awq" ]; then
  export CHAT_MODEL="${AWQ_CHAT_MODEL}"
  export CHAT_QUANTIZATION=awq
  export TOOL_MODEL="${AWQ_TOOL_MODEL}"
  export TOOL_QUANTIZATION=awq
fi

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

# Set GPU-specific defaults based on GPU type (AWQ optimized, mirroring main scripts)
case "${GPU_NAME}" in
  *H100*|*L40S*|*L40*)
    export VLLM_USE_V1=1
    export KV_DTYPE=${KV_DTYPE:-fp8}
    if [ "${HAS_FLASHINFER}" = "1" ]; then
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
    else
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
      log_warn "FlashInfer not available; using XFORMERS backend for AWQ."
    fi
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
    if [[ "${GPU_NAME}" == *H100* ]]; then
      export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
    fi
    export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
    export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
    export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
    export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    ;;
  *A100*)
    if [ "${HAS_FLASHINFER}" = "1" ]; then
      export VLLM_USE_V1=1
      export KV_DTYPE=${KV_DTYPE:-int8}
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
    else
      export VLLM_USE_V1=0
      export KV_DTYPE=${KV_DTYPE:-int8}
      export VLLM_ATTENTION_BACKEND=XFORMERS
    fi
    export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
    export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
    export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
    export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
    export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    export CUDA_DEVICE_MAX_CONNECTIONS=1
    ;;
  *)
    # Unknown GPU: prefer V1; prefer FlashInfer when available
    export VLLM_USE_V1=${VLLM_USE_V1:-1}
    export KV_DTYPE=${KV_DTYPE:-auto}
    if [ "${HAS_FLASHINFER}" = "1" ]; then
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
    else
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
    fi
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
log_info "  Quantization: ${QUANTIZATION:-awq}"
log_info "  KV dtype: ${KV_DTYPE}"
log_info "  Model calls: ${CONCURRENT_STATUS}"
