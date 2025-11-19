#!/usr/bin/env bash

# Limits, timeouts, and GPU fraction defaults

apply_limits_and_timeouts() {
  # Context and output limits
  export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5160}
  export CHAT_MAX_OUT=${CHAT_MAX_OUT:-150}
  export TOOL_MAX_OUT=${TOOL_MAX_OUT:-10}
  # Tool model max context length (Toolcall). 3000 allows for 1450 system + 350 user + 1200 history tokens
  export TOOL_MAX_LEN=${TOOL_MAX_LEN:-3000}

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
}


