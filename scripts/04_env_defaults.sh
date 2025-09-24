#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
source "${SCRIPT_DIR}/utils.sh"

log_info "Setting environment defaults"

USER_SET_CHAT_MODEL=0; if [ "${CHAT_MODEL+x}" = "x" ]; then USER_SET_CHAT_MODEL=1; fi
USER_SET_QUANT=0; if [ "${QUANTIZATION+x}" = "x" ]; then USER_SET_QUANT=1; fi
USER_SET_KV=0; if [ "${KV_DTYPE+x}" = "x" ]; then USER_SET_KV=1; fi
USER_SET_ARCH=0; if [ "${TORCH_CUDA_ARCH_LIST+x}" = "x" ]; then USER_SET_ARCH=1; fi

export CHAT_MODEL=${CHAT_MODEL:-SicariusSicariiStuff/Impish_Nemo_12B}
export TOOL_MODEL=${TOOL_MODEL:-MadeAgents/Hammer2.1-3b}

# QUANTIZATION/KV_DTYPE will be set after GPU detection; defaults to L40-class (fp8/fp8)
# Cap context to match the model until RoPE/YaRN is fixed  
export CHAT_MAX_LEN=${CHAT_MAX_LEN:-6144}
export CHAT_MAX_OUT=${CHAT_MAX_OUT:-200}
export TOOL_MAX_OUT=${TOOL_MAX_OUT:-10}
# Tool model max context length (Hammer). 2048 fits ~1.4k-token instructions comfortably.
export TOOL_MAX_LEN=${TOOL_MAX_LEN:-2048}
# GPU memory fractions (weights + KV). Use fractions only.
export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.75}
export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}
# Realtime by default: 0 = no throttle; set >0 to enable fake typing
export STREAM_RATE_TOKS_PER_S=${STREAM_RATE_TOKS_PER_S:-0}
# Optional tiny packet coalescer window (ms); 0 = off
export STREAM_FLUSH_MS=${STREAM_FLUSH_MS:-0}
export ENABLE_SPECULATIVE=${ENABLE_SPECULATIVE:-1}
export NUM_SPECULATIVE_TOKENS=${NUM_SPECULATIVE_TOKENS:-6}

# Buffer-then-flush knobs for parallel tool router
export TOOL_HARD_TIMEOUT_MS=${TOOL_HARD_TIMEOUT_MS:-400}
export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-1000}

# Text processing toggles (disabled by default for optimal benchmarking)
export TEXTPROC_ENABLE=${TEXTPROC_ENABLE:-0}
export TEXTPROC_REMOVE_EMOJIS=${TEXTPROC_REMOVE_EMOJIS:-1}
export TEXTPROC_CONVERT_NUMBERS=${TEXTPROC_CONVERT_NUMBERS:-1}

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

# --- GPU auto-detection for quantization defaults ---
GPU_NAME=""
if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1 || true)
fi
export DETECTED_GPU_NAME="${GPU_NAME}"

#
# KV cache policy:
#  - On Hopper/Ada (H100/L40S): allow FP8 KV (e5m2) but DISABLE prefix caching.
#  - On Ampere (A100): prefer fp16 KV (auto). FP8 KV can be unstable; avoid by default.
#
case "${GPU_NAME}" in
  *H100*|*L40S*|*L40*)
    if [ "${USER_SET_QUANT}" -eq 0 ]; then export QUANTIZATION=fp8; fi
    # On V1, --kv-cache-dtype is not supported. Use default (fp16/auto).
    if [ "${USER_SET_KV}" -eq 0 ]; then
      if [ "${VLLM_USE_V1:-1}" = "1" ]; then
        export KV_DTYPE=
      else
        export KV_DTYPE=fp8_e5m2
      fi
    fi
    if [ "${USER_SET_ARCH}" -eq 0 ]; then 
      if [[ "${GPU_NAME}" == *H100* ]]; then
        export TORCH_CUDA_ARCH_LIST=9.0
      else
        export TORCH_CUDA_ARCH_LIST=8.9  # L40S/L40
      fi
    fi
    export DISABLE_PREFIX_CACHE_FOR_KV_FP8=${DISABLE_PREFIX_CACHE_FOR_KV_FP8:-1}
    if [ "${USER_SET_CHAT_MODEL}" -eq 0 ] && [ "${CHAT_MODEL:-}" = "SicariusSicariiStuff/Impish_Nemo_12B" ]; then
      export CHAT_MODEL="SicariusSicariiStuff/Impish_Nemo_12B"
    fi
    # L40S specific tuning - optimized for concurrency and performance
    if [[ "${GPU_NAME}" == *L40S* ]] || [[ "${GPU_NAME}" == *L40* ]]; then
      export ENFORCE_EAGER=${ENFORCE_EAGER:-0}  # Enable CUDA graphs for better performance
      export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.70}
      export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}
      export MAX_NUM_BATCHED_TOKENS_CHAT=${MAX_NUM_BATCHED_TOKENS_CHAT:-768}  # Increased from 512
      export MAX_NUM_BATCHED_TOKENS_TOOL=${MAX_NUM_BATCHED_TOKENS_TOOL:-256}
      # Stream prebuffer and hard timeouts suitable for L40S
      export TOOL_HARD_TIMEOUT_MS=${TOOL_HARD_TIMEOUT_MS:-200}
      export TOOL_TIMEOUT_S=${TOOL_TIMEOUT_S:-0.5}
      export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-256}
      export GEN_TIMEOUT_S=${GEN_TIMEOUT_S:-20}
    fi
    ;;
  *A100*)
    if [ "${USER_SET_QUANT}" -eq 0 ]; then export QUANTIZATION=fp8; fi  # W8A16 on Ampere
    # On V1, --kv-cache-dtype is not supported. Use default (fp16/auto).
    if [ "${USER_SET_KV}" -eq 0 ]; then
      if [ "${VLLM_USE_V1:-1}" = "1" ]; then
        export KV_DTYPE=
      else
        export KV_DTYPE=auto
      fi
    fi
    if [ "${USER_SET_ARCH}" -eq 0 ]; then export TORCH_CUDA_ARCH_LIST=8.0; fi
    export DISABLE_PREFIX_CACHE_FOR_KV_FP8=${DISABLE_PREFIX_CACHE_FOR_KV_FP8:-1}
    if [ "${USER_SET_CHAT_MODEL}" -eq 0 ] && [ "${CHAT_MODEL:-}" = "SicariusSicariiStuff/Impish_Nemo_12B" ]; then
      export CHAT_MODEL="SicariusSicariiStuff/Impish_Nemo_12B"
    fi
    ;;
  *)
    # Unknown GPU: conservative defaults
    if [ "${USER_SET_QUANT}" -eq 0 ]; then export QUANTIZATION=fp8; fi
    # On V1, --kv-cache-dtype is not supported. Use default (fp16/auto).
    if [ "${USER_SET_KV}" -eq 0 ]; then
      if [ "${VLLM_USE_V1:-1}" = "1" ]; then
        export KV_DTYPE=
      else
        export KV_DTYPE=auto
      fi
    fi
    export DISABLE_PREFIX_CACHE_FOR_KV_FP8=${DISABLE_PREFIX_CACHE_FOR_KV_FP8:-1}
    ;;
esac

# Force GPTQ 4-bit path when requested
if [ "${FORCE_4BIT:-0}" = "1" ]; then
  export CHAT_MODEL="SicariusSicariiStuff/Impish_Nemo_12B_GPTQ_4-bit-128"
  export QUANTIZATION=gptq
  # KV cache quantization still applies to runtime KV; keep fp16 (auto) to be safe when mixing with GPTQ
  export KV_DTYPE=${KV_DTYPE:-auto}
  log_info "Overriding to 4-bit model (GPTQ): ${CHAT_MODEL} QUANTIZATION=${QUANTIZATION} KV_DTYPE=${KV_DTYPE}"
fi

# Ensure defaults if still unset (conservative behavior)
export QUANTIZATION=${QUANTIZATION:-fp8}
export KV_DTYPE=${KV_DTYPE:-auto}  # fp16 as safe fallback, not int8
export TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST:-8.0}

if [ -n "${DETECTED_GPU_NAME}" ]; then
  log_info "Detected GPU: ${DETECTED_GPU_NAME} → QUANTIZATION=${QUANTIZATION} KV_DTYPE=${KV_DTYPE} TORCH_CUDA_ARCH_LIST=${TORCH_CUDA_ARCH_LIST}"
else
  log_warn "GPU not detected; using conservative defaults: QUANTIZATION=${QUANTIZATION} KV_DTYPE=${KV_DTYPE}"
fi

