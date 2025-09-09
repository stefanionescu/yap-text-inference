#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Setting environment defaults"

export CHAT_MODEL=${CHAT_MODEL:-recoilme/recoilme-gemma-2-9B-v0.5}
export DRAFT_MODEL=${DRAFT_MODEL:-MadeAgents/Hammer2.1-3b}

export KV_DTYPE=${KV_DTYPE:-fp8}
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-4096}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-200}
export TOOL_MAX_OUT=${TOOL_MAX_OUT:-10}
# Prefer fixed GiB reservations; code converts GiB→fraction
export CHAT_GPU_GIB=${CHAT_GPU_GIB:-33.0}
export TOOL_GPU_GIB=${TOOL_GPU_GIB:-7.0}
# Fractions remain as fallback if GiB not set
export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.75}
export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.18}
export STREAM_RATE_TOKS_PER_S=${STREAM_RATE_TOKS_PER_S:-10}
export ENABLE_SPECULATIVE=${ENABLE_SPECULATIVE:-0}

# Text processing toggles
export TEXTPROC_ENABLE=${TEXTPROC_ENABLE:-1}
export TEXTPROC_REMOVE_EMOJIS=${TEXTPROC_REMOVE_EMOJIS:-1}
export TEXTPROC_CONVERT_NUMBERS=${TEXTPROC_CONVERT_NUMBERS:-1}

# Token limits (approx)
export HISTORY_MAX_TOKENS=${HISTORY_MAX_TOKENS:-3000}
export USER_UTT_MAX_TOKENS=${USER_UTT_MAX_TOKENS:-500}

# vLLM engine selection and attention backend
export VLLM_USE_V1=${VLLM_USE_V1:-1}
export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.9}

# Ensure LMCache YAML path is set for V1 connector
export LMCACHE_CONFIG_FILE=${LMCACHE_CONFIG_FILE:-${ROOT_DIR}/lmcache.yaml}


