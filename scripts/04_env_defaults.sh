#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Setting environment defaults"

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

# Validate required environment variables are set by main.sh (conditional on deploy mode)
if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_MODEL:-}" ]; then
  log_warn "Error: CHAT_MODEL must be set when DEPLOY_MODELS='both' or 'chat'"
  exit 1
fi

if [ "${DEPLOY_TOOL}" = "1" ] && [ -z "${TOOL_MODEL:-}" ]; then
  log_warn "Error: TOOL_MODEL must be set when DEPLOY_MODELS='both' or 'tool'"
  exit 1
fi

if [ -z "${QUANTIZATION:-}" ]; then
  log_warn "Error: QUANTIZATION environment variable must be set by main.sh"
  exit 1
fi

# Context and output limits
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5160}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-200}
export TOOL_MAX_OUT=${TOOL_MAX_OUT:-10}
# Tool model max context length (Hammer). 3000 allows for 1450 system + 350 user + 1200 history tokens
export TOOL_MAX_LEN=${TOOL_MAX_LEN:-3000}
# GPU memory fractions (weights + KV). Use fractions only.
export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.70}
export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}
# Optional tiny packet coalescer window (ms); 0 = off
export STREAM_FLUSH_MS=${STREAM_FLUSH_MS:-0}

# Buffer-then-flush knobs for parallel tool router
export TOOL_HARD_TIMEOUT_MS=${TOOL_HARD_TIMEOUT_MS:-300}
export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-1000}

# Concurrent model calling mode: 0=sequential, 1=concurrent (default)
export CONCURRENT_MODEL_CALL=${CONCURRENT_MODEL_CALL:-1}

# Token limits (approx)
export HISTORY_MAX_TOKENS=${HISTORY_MAX_TOKENS:-2400}
export USER_UTT_MAX_TOKENS=${USER_UTT_MAX_TOKENS:-350}

# Tool model specific token limits
export TOOL_HISTORY_TOKENS=${TOOL_HISTORY_TOKENS:-1200}  # Tool model context allocation
export TOOL_SYSTEM_TOKENS=${TOOL_SYSTEM_TOKENS:-1450}   # System prompt + response space

# vLLM engine selection; attention backend chosen below (FLASHINFER preferred)
export VLLM_USE_V1=${VLLM_USE_V1:-1}
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-}
export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=${VLLM_ALLOW_LONG_MAX_MODEL_LEN:-1}
export AWQ_CACHE_DIR="${ROOT_DIR}/.awq"

# Speed up subsequent installs: persist pip cache under repo (stop.sh keeps it by default)
export PIP_CACHE_DIR="${ROOT_DIR}/.pip_cache"
# Centralize heavy caches under the repo so wipe scripts can fully clean them
export HF_HOME="${ROOT_DIR}/.hf"
export TRANSFORMERS_CACHE="${HF_HOME}"
export HUGGINGFACE_HUB_CACHE="${HF_HOME}/hub"
export VLLM_CACHE_DIR="${ROOT_DIR}/.vllm_cache"
export TORCHINDUCTOR_CACHE_DIR="${ROOT_DIR}/.torch_inductor"
export TRITON_CACHE_DIR="${ROOT_DIR}/.triton"
export FLASHINFER_CACHE_DIR="${ROOT_DIR}/.flashinfer"
export XFORMERS_CACHE_DIR="${ROOT_DIR}/.xformers"

# Backend selection is centralized in Python. Only export if explicitly set.
if [ -n "${VLLM_ATTENTION_BACKEND:-}" ]; then
  export VLLM_ATTENTION_BACKEND
fi

# --- GPU detection and optimization ---
GPU_NAME=""
if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 || true)
fi
export DETECTED_GPU_NAME="${GPU_NAME}"

# Set GPU-specific defaults based on quantization mode and GPU type
case "${QUANTIZATION}" in
  fp8)
    # 8-bit mode optimizations
    case "${GPU_NAME}" in
      *H100*|*L40S*|*L40*)
        export KV_DTYPE=${KV_DTYPE:-fp8}
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
        if [[ "${GPU_NAME}" == *H100* ]]; then
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
        fi
        # Hopper/Ada optimizations for fp8
        export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
        export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
        export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
        export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
        export TOOL_HARD_TIMEOUT_MS=${TOOL_HARD_TIMEOUT_MS:-200}
        export TOOL_TIMEOUT_S=${TOOL_TIMEOUT_S:-0.5}
        export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-256}
        export GEN_TIMEOUT_S=${GEN_TIMEOUT_S:-60}
        ;;
    *A100*)
      export KV_DTYPE=${KV_DTYPE:-auto}  # fp16 preferred for A100 stability
      export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
      export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
      export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
      export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
      export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
      export CUDA_DEVICE_MAX_CONNECTIONS=1
      export TOOL_HARD_TIMEOUT_MS=${TOOL_HARD_TIMEOUT_MS:-300}
      export TOOL_TIMEOUT_S=${TOOL_TIMEOUT_S:-0.5}
      export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-1000}
      export GEN_TIMEOUT_S=${GEN_TIMEOUT_S:-60}
      ;;
      *)
        # Unknown GPU: conservative fp8 defaults
        export KV_DTYPE=${KV_DTYPE:-auto}
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
        ;;
    esac
    ;;
  awq)
    # 4-bit AWQ via vLLM auto-AWQ. Prefer V1 engine; KV dtype fp8 on Hopper/Ada if available.
    case "${GPU_NAME}" in
      *H100*|*L40S*|*L40*)
        export VLLM_USE_V1=1
        export KV_DTYPE=${KV_DTYPE:-fp8}
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
        # A100: V0 for max slots, keep KV fp16/auto for stability
        export VLLM_USE_V1=0
        export KV_DTYPE=${KV_DTYPE:-auto}
        export VLLM_ATTENTION_BACKEND=XFORMERS
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
        export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
        export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-512}
        export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
        ;;
      *)
        # Unknown GPU: conservative defaults
        export VLLM_USE_V1=${VLLM_USE_V1:-1}
        export KV_DTYPE=${KV_DTYPE:-auto}
        export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-XFORMERS}
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
        ;;
    esac
    ;;
  gptq_marlin)
    # 4-bit mode optimizations
    case "${GPU_NAME}" in
      *A100*)
        # A100: Use V0 engine + INT8 KV for maximum long-context slots
        export VLLM_USE_V1=0
        export KV_DTYPE=${KV_DTYPE:-int8}
        export VLLM_ATTENTION_BACKEND=XFORMERS
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
        log_info "A100 4-bit mode: V0 engine + INT8 KV for maximum context slots"
        ;;
      *H100*|*L40S*|*L40*)
        # Hopper/Ada: Prefer V1 engine + FP8 KV if backend supports it (Python enforces)
        export VLLM_USE_V1=1
        export KV_DTYPE=${KV_DTYPE:-fp8}
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
        if [[ "${GPU_NAME}" == *H100* ]]; then
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
        fi
        log_info "Hopper/Ada 4-bit mode: V1 engine preferred; backend decided in Python"
        ;;
      *)
        # Unknown GPU: conservative approach (V0 + auto KV)
        export VLLM_USE_V1=0
        export KV_DTYPE=${KV_DTYPE:-auto}
        export VLLM_ATTENTION_BACKEND=XFORMERS
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
        log_warn "Unknown GPU 4-bit mode: using conservative V0 + fp16 KV"
        ;;
    esac
    ;;
esac

# If awq is selected, prepare local quantized dirs and rewrite models to local paths.
if [ "${QUANTIZATION}" = "awq" ]; then
  mkdir -p "${AWQ_CACHE_DIR}"
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    CHAT_OUT_DIR="${AWQ_CACHE_DIR}/chat_awq"
    if [[ "${CHAT_MODEL}" == *GPTQ* ]]; then
      log_warn "AWQ selected but GPTQ chat model provided; refusing."
      exit 1
    fi
    if [ ! -f "${CHAT_OUT_DIR}/awq_config.json" ] && [ ! -f "${CHAT_OUT_DIR}/.awq_ok" ]; then
      log_info "Quantizing chat model to AWQ: ${CHAT_MODEL} -> ${CHAT_OUT_DIR}"
      "${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/src/quant/awq_quantize.py" --model "${CHAT_MODEL}" --out "${CHAT_OUT_DIR}" || {
        log_warn "AWQ quantization failed for chat model"
        exit 1
      }
    else
      log_info "Using existing AWQ chat model at ${CHAT_OUT_DIR}"
    fi
    export CHAT_MODEL="${CHAT_OUT_DIR}"
  fi
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    TOOL_OUT_DIR="${AWQ_CACHE_DIR}/tool_awq"
    if [ ! -f "${TOOL_OUT_DIR}/awq_config.json" ] && [ ! -f "${TOOL_OUT_DIR}/.awq_ok" ]; then
      log_info "Quantizing tool model to AWQ: ${TOOL_MODEL} -> ${TOOL_OUT_DIR}"
      "${ROOT_DIR}/.venv/bin/python" "${ROOT_DIR}/src/quant/awq_quantize.py" --model "${TOOL_MODEL}" --out "${TOOL_OUT_DIR}" || {
        log_warn "AWQ quantization failed for tool model"
        exit 1
      }
    else
      log_info "Using existing AWQ tool model at ${TOOL_OUT_DIR}"
    fi
    export TOOL_MODEL="${TOOL_OUT_DIR}"
  fi
fi

# Final defaults if still unset
export KV_DTYPE=${KV_DTYPE:-auto}
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}

CONCURRENT_STATUS="sequential"
if [ "${CONCURRENT_MODEL_CALL:-0}" = "1" ]; then
  CONCURRENT_STATUS="concurrent"
fi

log_info "Configuration: GPU=${DETECTED_GPU_NAME:-unknown}"
log_info "  Deploy mode: ${DEPLOY_MODELS} (chat=${DEPLOY_CHAT}, tool=${DEPLOY_TOOL})"
log_info "  Chat model: ${CHAT_MODEL}"
log_info "  Tool model: ${TOOL_MODEL}"
log_info "  Quantization: ${QUANTIZATION}"
log_info "  KV dtype: ${KV_DTYPE}"
log_info "  Model calls: ${CONCURRENT_STATUS}"

