#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Setting environment defaults"

export CHAT_MODEL=${CHAT_MODEL:-recoilme/recoilme-gemma-2-9B-v0.5}
export DRAFT_MODEL=${DRAFT_MODEL:-MadeAgents/Hammer2.1-3b}

export KV_DTYPE=${KV_DTYPE:-fp8}
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-7168}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-140}
export TOOL_MAX_OUT=${TOOL_MAX_OUT:-10}
export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.82}
export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.14}
export STREAM_RATE_TOKS_PER_S=${STREAM_RATE_TOKS_PER_S:-10}

# Text processing toggles
export TEXTPROC_ENABLE=${TEXTPROC_ENABLE:-1}
export TEXTPROC_REMOVE_EMOJIS=${TEXTPROC_REMOVE_EMOJIS:-1}
export TEXTPROC_CONVERT_NUMBERS=${TEXTPROC_CONVERT_NUMBERS:-1}

# Token limits (approx)
export HISTORY_MAX_TOKENS=${HISTORY_MAX_TOKENS:-3000}
export USER_UTT_MAX_TOKENS=${USER_UTT_MAX_TOKENS:-500}

# vLLM engine selection and attention backend
export VLLM_USE_V1=${VLLM_USE_V1:-0}
export VLLM_ATTENTION_BACKEND=${VLLM_ATTENTION_BACKEND:-FLASHINFER}


