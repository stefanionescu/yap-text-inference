#!/usr/bin/env bash

# Auto-select QUANTIZATION if not explicitly set
# Carefully handle mixed case: prequantized AWQ for one engine, float/GPTQ for the other
if [ -z "${QUANTIZATION:-}" ] || [ "${QUANTIZATION}" = "auto" ]; then
  CHAT_IS_AWQ=$([ "${CHAT_QUANTIZATION:-}" = "awq" ] && echo 1 || echo 0)
  TOOL_IS_AWQ=$([ "${TOOL_QUANTIZATION:-}" = "awq" ] && echo 1 || echo 0)

  if [ "${CHAT_IS_AWQ}" = "1" ] && [ "${TOOL_IS_AWQ}" = "1" ]; then
    export QUANTIZATION=awq
  elif [ "${CHAT_IS_AWQ}" = "1" ] && [ "${DEPLOY_TOOL}" = "1" ]; then
    # Chat is AWQ prequantized; select tool quantization based on its model name
    if is_gptq_name "${TOOL_MODEL}"; then
      export QUANTIZATION=gptq_marlin
      export TOOL_QUANTIZATION=${TOOL_QUANTIZATION:-gptq_marlin}
    else
      export QUANTIZATION=fp8
      export TOOL_QUANTIZATION=${TOOL_QUANTIZATION:-fp8}
    fi
  elif [ "${TOOL_IS_AWQ}" = "1" ] && [ "${DEPLOY_CHAT}" = "1" ]; then
    if is_gptq_name "${CHAT_MODEL}"; then
      export QUANTIZATION=gptq_marlin
      export CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-gptq_marlin}
    else
      export QUANTIZATION=fp8
      export CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-fp8}
    fi
  else
    # No prequantized AWQ provided; decide per models
    CHAT_Q=fp8; TOOL_Q=fp8
    if [ "${DEPLOY_CHAT}" = "1" ] && is_gptq_name "${CHAT_MODEL}"; then CHAT_Q=gptq_marlin; fi
    if [ "${DEPLOY_TOOL}" = "1" ] && is_gptq_name "${TOOL_MODEL}"; then TOOL_Q=gptq_marlin; fi
    # Prefer using chat as the global signal (Python allows per-engine override too)
    export QUANTIZATION=${CHAT_Q}
    export CHAT_QUANTIZATION=${CHAT_QUANTIZATION:-${CHAT_Q}}
    export TOOL_QUANTIZATION=${TOOL_QUANTIZATION:-${TOOL_Q}}
  fi
fi


