#!/usr/bin/env bash

# Limits, timeouts, and GPU fraction defaults

apply_limits_and_timeouts() {
  # Context and output limits
  export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5025}
  export CHAT_MAX_OUT=${CHAT_MAX_OUT:-150}
  export TOOL_MAX_OUT=${TOOL_MAX_OUT:-100}
  # Tool model max context length (Toolcall). 4650 allows for 3400 system + 900 history tokens + 350 user
  export TOOL_MAX_LEN=${TOOL_MAX_LEN:-4650}

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

  # Token limits (approx)
  export HISTORY_MAX_TOKENS=${HISTORY_MAX_TOKENS:-3000}
  export USER_UTT_MAX_TOKENS=${USER_UTT_MAX_TOKENS:-350}

  # Prefill batching overrides
  export MAX_NUM_SEQS_CHAT=${MAX_NUM_SEQS_CHAT:-32}
  export MAX_NUM_SEQS_TOOL=${MAX_NUM_SEQS_TOOL:-32}
}


