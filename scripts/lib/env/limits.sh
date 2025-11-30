#!/usr/bin/env bash

# Limits, timeouts, and GPU fraction defaults

apply_limits_and_timeouts() {
  # Context and output limits
  export CHAT_MAX_LEN=${CHAT_MAX_LEN:-4425}
  export CHAT_MAX_OUT=${CHAT_MAX_OUT:-150}
  export TOOL_MAX_OUT=${TOOL_MAX_OUT:-25}
  # Tool model max context length (Toolcall). 3050 allows for 1800 system + 900 history tokens + 350 user
  export TOOL_MAX_LEN=${TOOL_MAX_LEN:-3050}

  # GPU memory fractions (weights + KV). Use fractions only.
  # Adjust based on deployment mode: single model gets 90%, both models split memory
  if [ "${DEPLOY_MODELS:-both}" = "both" ]; then
    export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.70}
    export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}
  else
    export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.90}
    export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.90}
  fi

  # Optional tiny packet coalescer window (ms); 0 = off
  export STREAM_FLUSH_MS=${STREAM_FLUSH_MS:-0}

  # Buffer-then-flush knobs for parallel tool router
  export TOOL_HARD_TIMEOUT_MS=${TOOL_HARD_TIMEOUT_MS:-500}
  export PREBUFFER_MAX_CHARS=${PREBUFFER_MAX_CHARS:-1000}

  # Concurrent model calling mode: 0=sequential (default), 1=concurrent
  export CONCURRENT_MODEL_CALL=${CONCURRENT_MODEL_CALL:-0}

  # Token limits (approx)
  export HISTORY_MAX_TOKENS=${HISTORY_MAX_TOKENS:-2400}
  export USER_UTT_MAX_TOKENS=${USER_UTT_MAX_TOKENS:-350}

  # Tool model specific token limits
  export TOOL_HISTORY_TOKENS=${TOOL_HISTORY_TOKENS:-900}  # Tool model context allocation
  export TOOL_PROMPT_MAX_TOKENS=${TOOL_PROMPT_MAX_TOKENS:-1800}   # System prompt + response space

  # Prefill batching overrides
  export MAX_NUM_SEQS_CHAT=${MAX_NUM_SEQS_CHAT:-32}
  export MAX_NUM_SEQS_TOOL=${MAX_NUM_SEQS_TOOL:-32}
}


