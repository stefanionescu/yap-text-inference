#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Setting environment defaults"

# Validate required environment variables are set by main.sh
if [ -z "${CHAT_MODEL:-}" ]; then
  log_warn "Error: CHAT_MODEL environment variable must be set by main.sh"
  exit 1
fi

if [ -z "${QUANTIZATION:-}" ]; then
  log_warn "Error: QUANTIZATION environment variable must be set by main.sh"
  exit 1
fi

export TOOL_MODEL=${TOOL_MODEL:-MadeAgents/Hammer2.1-3b}

# Context and output limits
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5760}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-200}
export TOOL_MAX_OUT=${TOOL_MAX_OUT:-10}
# Tool model max context length (Hammer). 1536 fits ~1.1k-token instructions comfortably.
export TOOL_MAX_LEN=${TOOL_MAX_LEN:-1536}
# GPU memory fractions (weights + KV). Use fractions only.
export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.70}
export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}
# Optional tiny packet coalescer window (ms); 0 = off
export STREAM_FLUSH_MS=${STREAM_FLUSH_MS:-0}

# Buffer-then-flush knobs for parallel tool router
export TOOL_HARD_TIMEOUT_MS=${TOOL_HARD_TIMEOUT_MS:-300}
export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-1000}

# Concurrent model calling mode: 0=sequential (default), 1=concurrent
export CONCURRENT_MODEL_CALL=${CONCURRENT_MODEL_CALL:-0}

# Token limits (approx)
export HISTORY_MAX_TOKENS=${HISTORY_MAX_TOKENS:-3000}
export USER_UTT_MAX_TOKENS=${USER_UTT_MAX_TOKENS:-350}

# vLLM engine selection; attention backend chosen below (FLASHINFER preferred)
export VLLM_USE_V1=${VLLM_USE_V1:-1}
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-}
export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
export VLLM_ALLOW_LONG_MAX_MODEL_LEN=${VLLM_ALLOW_LONG_MAX_MODEL_LEN:-1}

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

# --- Attention backend selection (prefer FLASHINFER when installed) ---
# User cannot override: always auto-select based on availability of flashinfer.
if python - <<'PY'
import sys
try:
    import flashinfer  # noqa: F401
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
then
  export VLLM_ATTENTION_BACKEND=FLASHINFER
else
  export VLLM_ATTENTION_BACKEND=XFORMERS
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
        export KV_DTYPE=${KV_DTYPE:-auto}  # fp16 for A100 stability
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
        # Hopper/Ada: Keep V1 engine + auto FP8 KV + FlashInfer
        export VLLM_USE_V1=1
        export KV_DTYPE=${KV_DTYPE:-fp8}
        # VLLM_ATTENTION_BACKEND already set to FLASHINFER globally
        export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}
        if [[ "${GPU_NAME}" == *H100* ]]; then
          export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-9.0}
        fi
        log_info "Hopper/Ada 4-bit mode: V1 engine + auto FP8 KV with FlashInfer"
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

# Final defaults if still unset
export KV_DTYPE=${KV_DTYPE:-auto}
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}

log_info "Configuration: GPU=${DETECTED_GPU_NAME:-unknown} MODEL=${CHAT_MODEL} QUANTIZATION=${QUANTIZATION} KV_DTYPE=${KV_DTYPE}"

