#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Setting environment defaults (Base image)"

# Prefer the embedded venv
if [ -f "/opt/venv/bin/python" ]; then
  PY_BIN="/opt/venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PY_BIN="python"
else
  PY_BIN=""
fi

# Detect FlashInfer availability (optional fast-path)
HAS_FLASHINFER=0
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

# Deployment selection
export DEPLOY_MODELS=${DEPLOY_MODELS:-both}
case "${DEPLOY_MODELS}" in
  both|chat|tool) ;; 
  *) log_warn "Invalid DEPLOY_MODELS='${DEPLOY_MODELS}', defaulting to 'both'"; export DEPLOY_MODELS=both;;
esac

# Convenience flags
DEPLOY_CHAT=0; DEPLOY_TOOL=0
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "chat" ]; then DEPLOY_CHAT=1; fi
if [ "${DEPLOY_MODELS}" = "both" ] || [ "${DEPLOY_MODELS}" = "tool" ]; then DEPLOY_TOOL=1; fi
export DEPLOY_CHAT DEPLOY_TOOL

# Check for models provided by the user
CHAT_MODEL_IN=${CHAT_MODEL:-}
TOOL_MODEL_IN=${TOOL_MODEL:-}
AWQ_CHAT_MODEL_IN=${AWQ_CHAT_MODEL:-}
AWQ_TOOL_MODEL_IN=${AWQ_TOOL_MODEL:-}

# Enforce exactly one source per engine (env-level). Do not allow both float/GPTQ and AWQ vars simultaneously.
if [ -n "${AWQ_CHAT_MODEL_IN}" ] && [ -n "${CHAT_MODEL_IN}" ]; then
  log_error "Specify only one chat model source: either AWQ_CHAT_MODEL or CHAT_MODEL (not both)"
  exit 1
fi
if [ -n "${AWQ_TOOL_MODEL_IN}" ] && [ -n "${TOOL_MODEL_IN}" ]; then
  log_error "Specify only one tool model source: either AWQ_TOOL_MODEL or TOOL_MODEL (not both)"
  exit 1
fi

# Prefer preloaded models if env not given
PRELOADED_CHAT_DIR="/app/models/chat"
PRELOADED_TOOL_DIR="/app/models/tool"
PRELOADED_CHAT_AWQ_DIR="/app/models/chat_awq"
PRELOADED_TOOL_AWQ_DIR="/app/models/tool_awq"

file_exists() { [ -e "$1" ]; }

# Determine if pre-quantized AWQ dirs exist
HAS_PRELOADED_AWQ_CHAT=0
HAS_PRELOADED_AWQ_TOOL=0
if [ -f "${PRELOADED_CHAT_AWQ_DIR}/awq_config.json" ] || [ -f "${PRELOADED_CHAT_AWQ_DIR}/.awq_ok" ]; then
  HAS_PRELOADED_AWQ_CHAT=1
fi
if [ -f "${PRELOADED_TOOL_AWQ_DIR}/awq_config.json" ] || [ -f "${PRELOADED_TOOL_AWQ_DIR}/.awq_ok" ]; then
  HAS_PRELOADED_AWQ_TOOL=1
fi

# Resolve model sources in priority order: explicit env -> preloaded AWQ -> preloaded float/GPTQ
if [ "${DEPLOY_CHAT}" = "1" ]; then
  if [ -n "${AWQ_CHAT_MODEL_IN}" ]; then
    export CHAT_MODEL="${AWQ_CHAT_MODEL_IN}"; export CHAT_QUANTIZATION=awq
  elif [ "${HAS_PRELOADED_AWQ_CHAT}" = "1" ]; then
    export CHAT_MODEL="${PRELOADED_CHAT_AWQ_DIR}"; export CHAT_QUANTIZATION=awq
  elif [ -n "${CHAT_MODEL_IN}" ]; then
    export CHAT_MODEL="${CHAT_MODEL_IN}"
  elif [ -d "${PRELOADED_CHAT_DIR}" ]; then
    export CHAT_MODEL="${PRELOADED_CHAT_DIR}"
  fi
fi

if [ "${DEPLOY_TOOL}" = "1" ]; then
  if [ -n "${AWQ_TOOL_MODEL_IN}" ]; then
    export TOOL_MODEL="${AWQ_TOOL_MODEL_IN}"; export TOOL_QUANTIZATION=awq
  elif [ "${HAS_PRELOADED_AWQ_TOOL}" = "1" ]; then
    export TOOL_MODEL="${PRELOADED_TOOL_AWQ_DIR}"; export TOOL_QUANTIZATION=awq
  elif [ -n "${TOOL_MODEL_IN}" ]; then
    export TOOL_MODEL="${TOOL_MODEL_IN}"
  elif [ -d "${PRELOADED_TOOL_DIR}" ]; then
    export TOOL_MODEL="${PRELOADED_TOOL_DIR}"
  fi
fi

# Guard required models
if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
  log_error "CHAT_MODEL must be specified (env or preloaded) when deploying chat"
  exit 1
fi
if [ "${DEPLOY_TOOL}" = "1" ] && [ -z "${TOOL_MODEL:-}" ]; then
  log_error "TOOL_MODEL must be specified (env or preloaded) when deploying tool"
  exit 1
fi

norm_lower() {
  echo "$1" | tr '[:upper:]' '[:lower:]'
}

is_gptq_name() {
  case "$(norm_lower "$1")" in
    *gptq*) return 0;;
    *) return 1;;
  esac
}

# Default concurrent mode ON for Docker; user can set CONCURRENT_MODEL_CALL=0 for sequential
export CONCURRENT_MODEL_CALL=${CONCURRENT_MODEL_CALL:-1}

# Auto-select QUANTIZATION if not explicitly set
# Carefully handle mixed case: prequantized AWQ for one engine, float/GPTQ for the other
if [ -z "${QUANTIZATION:-}" ] || [ "${QUANTIZATION}" = "auto" ]; then
  CHAT_IS_AWQ=$([ "${CHAT_QUANTIZATION:-}" = "awq" ] && echo 1 || echo 0)
  TOOL_IS_AWQ=$([ "${TOOL_QUANTIZATION:-}" = "awq" ] && echo 1 || echo 0)

  if [ "${CHAT_IS_AWQ}" = "1" ] && [ "${TOOL_IS_AWQ}" = "1" ]; then
    export QUANTIZATION=awq
  elif [ "${CHAT_IS_AWQ}" = "1" ] && [ "${DEPLOY_TOOL}" = "1" ]; then
    # Chat is AWQ prequantized; select tool quantization based on its model name
    if is_gptq_name "${TOOL_MODEL}"; then
      export QUANTIZATION=gptq_marlin
      export TOOL_QUANTIZATION=${TOOL_QUANTIZATION:-gptq_marlin}
    else
      export QUANTIZATION=fp8
      export TOOL_QUANTIZATION=${TOOL_QUANTIZATION:-fp8}
    fi
  elif [ "${TOOL_IS_AWQ}" = "1" ] && [ "${DEPLOY_CHAT}" = "1" ]; then
    if is_gptq_name "${CHAT_MODEL}"; then
      export QUANTIZATION=gptq_marlin
      export CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-gptq_marlin}
    else
      export QUANTIZATION=fp8
      export CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-fp8}
    fi
  else
    # No prequantized AWQ provided; decide per models
    CHAT_Q=fp8; TOOL_Q=fp8
    if [ "${DEPLOY_CHAT}" = "1" ] && is_gptq_name "${CHAT_MODEL}"; then CHAT_Q=gptq_marlin; fi
    if [ "${DEPLOY_TOOL}" = "1" ] && is_gptq_name "${TOOL_MODEL}"; then TOOL_Q=gptq_marlin; fi
    # Prefer using chat as the global signal (Python allows per-engine override too)
    export QUANTIZATION=${CHAT_Q}
    export CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-${CHAT_Q}}
    export TOOL_QUANTIZATION=${TOOL_QUANTIZATION:-${TOOL_Q}}
  fi
fi

# Context and output limits
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5160}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-200}
export TOOL_MAX_OUT=${TOOL_MAX_OUT:-10}
export TOOL_MAX_LEN=${TOOL_MAX_LEN:-3000}

# GPU memory allocation
if [ "${DEPLOY_MODELS}" = "both" ]; then
  export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.70}
  export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}
else
  export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.90}
  export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.90}
fi

# vLLM toggles
export VLLM_USE_V1=${VLLM_USE_V1:-1}
export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=${VLLM_ALLOW_LONG_MAX_MODEL_LEN:-1}

# GPU detection and backend selection
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
        if [[ "${GPU_NAME}" == *H100* ]]; then export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}; fi
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
  gptq|gptq_marlin)
    export QUANTIZATION=gptq_marlin
    export KV_DTYPE=${KV_DTYPE:-fp8}
    if [ "${HAS_FLASHINFER}" = "1" ]; then
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
    else
      export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
    fi
    ;;
  awq)
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
        if [[ "${GPU_NAME}" == *H100* ]]; then export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}; fi
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
    ;;
esac

# AWQ upload controls (only used if QUANTIZATION=awq and local quant is performed)
export HF_AWQ_PUSH=${HF_AWQ_PUSH:-0}
export HF_AWQ_CHAT_REPO=${HF_AWQ_CHAT_REPO:-"your-org/chat-awq"}
export HF_AWQ_TOOL_REPO=${HF_AWQ_TOOL_REPO:-"your-org/tool-awq"}
export HF_AWQ_BRANCH=${HF_AWQ_BRANCH:-main}
export HF_AWQ_PRIVATE=${HF_AWQ_PRIVATE:-1}
export HF_AWQ_ALLOW_CREATE=${HF_AWQ_ALLOW_CREATE:-1}
export HF_AWQ_COMMIT_MSG_CHAT=${HF_AWQ_COMMIT_MSG_CHAT:-}
export HF_AWQ_COMMIT_MSG_TOOL=${HF_AWQ_COMMIT_MSG_TOOL:-}

# Final defaults
export KV_DTYPE=${KV_DTYPE:-auto}
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}

CONCURRENT_STATUS="sequential"
if [ "${CONCURRENT_MODEL_CALL:-1}" = "1" ]; then CONCURRENT_STATUS="concurrent"; fi

log_info "Docker Base Configuration:"
log_info "  GPU: ${DETECTED_GPU_NAME:-unknown}"
log_info "  Deploy mode: ${DEPLOY_MODELS} (chat=${DEPLOY_CHAT}, tool=${DEPLOY_TOOL})"
log_info "  Chat model: ${CHAT_MODEL:-none}"
log_info "  Tool model: ${TOOL_MODEL:-none}"
log_info "  Quantization: ${QUANTIZATION} (chat=${CHAT_QUANTIZATION:-auto}, tool=${TOOL_QUANTIZATION:-auto})"
log_info "  KV dtype: ${KV_DTYPE}"
log_info "  Model calls: ${CONCURRENT_STATUS}"


