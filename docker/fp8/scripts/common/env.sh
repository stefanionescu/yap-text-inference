#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Setting environment defaults (FP8/GPTQ auto)"

# Detect FlashInfer availability (optional fast-path)
HAS_FLASHINFER=0
if [ -f "/opt/venv/bin/python" ]; then
  PY_BIN="/opt/venv/bin/python"
elif [ -f "${SCRIPT_DIR}/../../../.venv/bin/python" ]; then
  PY_BIN="${SCRIPT_DIR}/../../../.venv/bin/python"
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

# Required: models provided by user
export CHAT_MODEL=${CHAT_MODEL:-}
export TOOL_MODEL=${TOOL_MODEL:-}

if [ -z "${CHAT_MODEL:-}" ] && [ -z "${TOOL_MODEL:-}" ]; then
  log_error "CHAT_MODEL/TOOL_MODEL must be provided in FP8/GPTQ mode"
  exit 1
fi

# Deployment mode (default both)
export DEPLOY_MODELS=${DEPLOY_MODELS:-both}

# Auto quantization selection if QUANTIZATION not preset
if [ -z "${QUANTIZATION:-}" ] || [ "${QUANTIZATION}" = "auto" ]; then
  if [[ "${CHAT_MODEL:-}" == *GPTQ* ]]; then
    export QUANTIZATION=gptq_marlin
  else
    export QUANTIZATION=fp8
  fi
fi

# Per-engine overrides for clarity
case "${QUANTIZATION}" in
  fp8)
    export CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-fp8}
    export TOOL_QUANTIZATION=${TOOL_QUANTIZATION:-fp8}
    ;;
  gptq|gptq_marlin)
    export QUANTIZATION=gptq_marlin
    export CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-gptq_marlin}
    export TOOL_QUANTIZATION=${TOOL_QUANTIZATION:-gptq_marlin}
    ;;
  *)
    log_warn "Unexpected QUANTIZATION='${QUANTIZATION}', falling back to fp8"
    export QUANTIZATION=fp8
    export CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-fp8}
    export TOOL_QUANTIZATION=${TOOL_QUANTIZATION:-fp8}
    ;;
esac

# Context and output limits
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5160}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-200}
export TOOL_MAX_OUT=${TOOL_MAX_OUT:-10}
export TOOL_MAX_LEN=${TOOL_MAX_LEN:-3000}

# GPU memory fractions (weights + KV). Use fractions only.
if [ "${DEPLOY_MODELS}" = "both" ]; then
  export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.70}
  export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}
else
  export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.90}
  export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.90}
fi

# Concurrent model calling mode: 0=sequential, 1=concurrent (default: concurrent for Docker)
export CONCURRENT_MODEL_CALL=${CONCURRENT_MODEL_CALL:-1}

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

case "${QUANTIZATION}" in
  fp8)
    case "${GPU_NAME}" in
      *H100*|*L40S*|*L40*)
        export KV_DTYPE=${KV_DTYPE:-fp8}
        if [ "${HAS_FLASHINFER}" = "1" ]; then
          export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
        else
          export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
          log_warn "FlashInfer not available; using XFORMERS backend for FP8."
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
        export VLLM_USE_V1=0
        export KV_DTYPE=${KV_DTYPE:-int8}
        export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
        export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
        export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
        export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
        export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
        export CUDA_DEVICE_MAX_CONNECTIONS=1
        ;;
      *)
        export KV_DTYPE=${KV_DTYPE:-fp8}
        if [ "${HAS_FLASHINFER}" = "1" ]; then
          export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
        else
          export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
        fi
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
        ;;
    esac
    ;;
  gptq_marlin)
    # GPTQ path: prefer V1 + FP8 KV if backend supports it (Python will enforce)
    export VLLM_USE_V1=${VLLM_USE_V1:-1}
    export KV_DTYPE=${KV_DTYPE:-fp8}
    if [ "${HAS_FLASHINFER}" = "1" ]; then
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
    else
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
    fi
    ;;
esac

# Final defaults if still unset
export KV_DTYPE=${KV_DTYPE:-auto}
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}

CONCURRENT_STATUS="sequential"
if [ "${CONCURRENT_MODEL_CALL:-1}" = "1" ]; then
  CONCURRENT_STATUS="concurrent"
fi

log_info "Docker FP8/GPTQ Configuration:"
log_info "  GPU: ${DETECTED_GPU_NAME:-unknown}"
log_info "  Deploy mode: ${DEPLOY_MODELS}"
log_info "  Chat model: ${CHAT_MODEL:-none}"
log_info "  Tool model: ${TOOL_MODEL:-none}"
log_info "  Quantization: ${QUANTIZATION} (chat=${CHAT_QUANTIZATION}, tool=${TOOL_QUANTIZATION})"
log_info "  KV dtype: ${KV_DTYPE}"
log_info "  Model calls: ${CONCURRENT_STATUS}"


