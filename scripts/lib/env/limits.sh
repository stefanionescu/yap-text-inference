#!/usr/bin/env bash

# Limits, timeouts, and GPU fraction defaults

apply_limits_and_timeouts() {
  # Context and output limits
  export CHAT_MAX_LEN=${CHAT_MAX_LEN:-5525}
  export CHAT_MAX_OUT=${CHAT_MAX_OUT:-150}
  if [ "${DEPLOY_MODELS:-both}" = "both" ]; then
    export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.70}
  else
    export CHAT_GPU_FRAC=${CHAT_GPU_FRAC:-0.90}
  fi

  if [ "${DEPLOY_MODELS:-both}" = "both" ]; then
    export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.20}
  else
    export TOOL_GPU_FRAC=${TOOL_GPU_FRAC:-0.90}
  fi

  # Optional tiny packet coalescer window (ms); 0 = off
  export STREAM_FLUSH_MS=${STREAM_FLUSH_MS:-0}

  # Token limits (approx)
  export HISTORY_MAX_TOKENS=${HISTORY_MAX_TOKENS:-3000}
  export USER_UTT_MAX_TOKENS=${USER_UTT_MAX_TOKENS:-500}

  # Prefill batching overrides
  export MAX_NUM_SEQS_CHAT=${MAX_NUM_SEQS_CHAT:-32}
}


