#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Setting environment defaults"

export CHAT_MODEL=${CHAT_MODEL:-recoilme/recoilme-gemma-2-9B-v0.5}
export TOOL_MODEL=${TOOL_MODEL:-MadeAgents/Hammer2.1-3b}

export KV_DTYPE=${KV_DTYPE:-fp8_e5m2}
export WEIGHT_QUANTIZATION=${WEIGHT_QUANTIZATION:-none}
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-8192}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-200}
export TOOL_MAX_OUT=${TOOL_MAX_OUT:-10}
# Tool model max context length (Hammer). 2048 fits ~1.4k-token instructions comfortably.
export TOOL_MAX_LEN=${TOOL_MAX_LEN:-2048}

#############################################
# Detect total GPU memory (robust, prefers venv Python, falls back to nvidia-smi)
#############################################
TOTAL_GIB=0

# Prefer venv Python torch if available
PY_BIN=""
if [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
  PY_BIN="${ROOT_DIR}/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PY_BIN="$(command -v python)"
fi

if [ -n "${PY_BIN}" ]; then
  set +e
  TOTAL_GIB="$(${PY_BIN} - <<'PY'
try:
  import torch
  print(int(torch.cuda.get_device_properties(0).total_memory/(1024**3)))
except Exception:
  print(0)
PY
  )"
  set -e
fi

# Fallback to nvidia-smi total memory (handles non-venv python or torch missing)
if [ "${TOTAL_GIB}" = "0" ] || [ -z "${TOTAL_GIB}" ]; then
  if command -v nvidia-smi >/dev/null 2>&1; then
    set +e
    TOTAL_MIB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -n1 | tr -d ' \t')
    set -e
    if [ -n "${TOTAL_MIB}" ]; then
      TOTAL_GIB=$(( TOTAL_MIB / 1024 ))
    fi
  fi
fi

# MIG-aware fallback: infer from MIG slice name (e.g., 1g.10gb)
if [ "${TOTAL_GIB}" = "0" ] || [ -z "${TOTAL_GIB}" ]; then
  if command -v nvidia-smi >/dev/null 2>&1; then
    set +e
    MIG_GB=$(nvidia-smi -L 2>/dev/null | grep -i 'MIG' | head -n1 | grep -oE '[0-9]+gb' | tr -dc '0-9')
    set -e
    if [ -n "${MIG_GB}" ]; then
      TOTAL_GIB="${MIG_GB}"
    fi
  fi
fi

# Defaults for 40G/80G/MIG; leave headroom for fragmentation
if [ -z "${TOTAL_GIB}" ] || [ "${TOTAL_GIB}" = "0" ]; then
  # Unknown GPU; fall back to conservative splits
  export CHAT_GPU_GIB=${CHAT_GPU_GIB:-24.0}
  export TOOL_GPU_GIB=${TOOL_GPU_GIB:-6.0}
elif [ "${TOTAL_GIB}" -ge 70 ]; then
  export CHAT_GPU_GIB=${CHAT_GPU_GIB:-64.0}
  export TOOL_GPU_GIB=${TOOL_GPU_GIB:-12.0}
elif [ "${TOTAL_GIB}" -ge 35 ]; then
  export CHAT_GPU_GIB=${CHAT_GPU_GIB:-32.0}
  export TOOL_GPU_GIB=${TOOL_GPU_GIB:-8.0}
else
  # Small MIG slice (e.g., 10–20 GiB)
  # Reserve ~80% for chat, ~15–20% for tool
  CHAT_DEF=$(( TOTAL_GIB * 80 / 100 ))
  TOOL_DEF=$(( TOTAL_GIB * 18 / 100 ))
  # Ensure minimums
  if [ "${CHAT_DEF}" -lt 8 ]; then CHAT_DEF=8; fi
  if [ "${TOOL_DEF}" -lt 2 ]; then TOOL_DEF=2; fi
  export CHAT_GPU_GIB=${CHAT_GPU_GIB:-${CHAT_DEF}.0}
  export TOOL_GPU_GIB=${TOOL_GPU_GIB:-${TOOL_DEF}.0}
fi
# Fractions remain as fallback if GiB not set
export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.70}
export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}

# Realtime by default: 0 = no throttle; set >0 to enable fake typing
export STREAM_RATE_TOKS_PER_S=${STREAM_RATE_TOKS_PER_S:-0}
# Optional tiny packet coalescer window (ms); 0 = off
export STREAM_FLUSH_MS=${STREAM_FLUSH_MS:-0}
export ENABLE_SPECULATIVE=${ENABLE_SPECULATIVE:-0}
export NUM_SPECULATIVE_TOKENS=${NUM_SPECULATIVE_TOKENS:-6}

# Prefill chunk sizing (A100-friendly throughput defaults)
export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-1024}
export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-1024}

# Buffer-then-flush knobs for parallel tool router
export TOOL_HARD_TIMEOUT_MS=${TOOL_HARD_TIMEOUT_MS:-300}
export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-8000}

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
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}

# Centralize heavy caches under the repo so wipe scripts can fully clean them
export HF_HOME="${ROOT_DIR}/.hf"
export TRANSFORMERS_CACHE="${HF_HOME}"
export HUGGINGFACE_HUB_CACHE="${HF_HOME}/hub"
export VLLM_CACHE_DIR="${ROOT_DIR}/.vllm_cache"
export TORCHINDUCTOR_CACHE_DIR="${ROOT_DIR}/.torch_inductor"
export TRITON_CACHE_DIR="${ROOT_DIR}/.triton"
export FLASHINFER_CACHE_DIR="${ROOT_DIR}/.flashinfer"
export XFORMERS_CACHE_DIR="${ROOT_DIR}/.xformers"

