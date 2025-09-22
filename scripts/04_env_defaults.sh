#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Setting environment defaults"

export CHAT_MODEL=${CHAT_MODEL:-recoilme/recoilme-gemma-2-9B-v0.5}
export TOOL_MODEL=${TOOL_MODEL:-MadeAgents/Hammer2.1-3b}

export KV_DTYPE=${KV_DTYPE:-fp8}
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-8192}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-200}
export TOOL_MAX_OUT=${TOOL_MAX_OUT:-10}
# Tool model max context length (Hammer). 2048 fits ~1.4k-token instructions comfortably.
export TOOL_MAX_LEN=${TOOL_MAX_LEN:-2048}
# Prefer fixed GiB reservations; code converts GiB→fraction
export CHAT_GPU_GIB=${CHAT_GPU_GIB:-33.0}
export TOOL_GPU_GIB=${TOOL_GPU_GIB:-7.0}
# Fractions remain as fallback if GiB not set
export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.75}
export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}
# Realtime by default: 0 = no throttle; set >0 to enable fake typing
export STREAM_RATE_TOKS_PER_S=${STREAM_RATE_TOKS_PER_S:-0}
# Optional tiny packet coalescer window (ms); 0 = off
export STREAM_FLUSH_MS=${STREAM_FLUSH_MS:-0}
export ENABLE_SPECULATIVE=${ENABLE_SPECULATIVE:-0}

# Buffer-then-flush knobs for parallel tool router
export TOOL_HARD_TIMEOUT_MS=${TOOL_HARD_TIMEOUT_MS:-300}
export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-8000}

# Text processing toggles
export TEXTPROC_ENABLE=${TEXTPROC_ENABLE:-1}
export TEXTPROC_REMOVE_EMOJIS=${TEXTPROC_REMOVE_EMOJIS:-1}
export TEXTPROC_CONVERT_NUMBERS=${TEXTPROC_CONVERT_NUMBERS:-1}

# Token limits (approx)
export HISTORY_MAX_TOKENS=${HISTORY_MAX_TOKENS:-3000}
export USER_UTT_MAX_TOKENS=${USER_UTT_MAX_TOKENS:-350}

# vLLM engine selection and attention backend
export VLLM_USE_V1=${VLLM_USE_V1:-1}
export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}
export ENFORCE_EAGER=${ENFORCE_EAGER:-0}
# Centralize heavy caches under the repo so wipe scripts can fully clean them
export HF_HOME="${ROOT_DIR}/.hf"
export TRANSFORMERS_CACHE="${HF_HOME}"
export HUGGINGFACE_HUB_CACHE="${HF_HOME}/hub"
export VLLM_CACHE_DIR="${ROOT_DIR}/.vllm_cache"
export TORCHINDUCTOR_CACHE_DIR="${ROOT_DIR}/.torch_inductor"
export TRITON_CACHE_DIR="${ROOT_DIR}/.triton"
export FLASHINFER_CACHE_DIR="${ROOT_DIR}/.flashinfer"
export XFORMERS_CACHE_DIR="${ROOT_DIR}/.xformers"

