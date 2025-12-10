#!/usr/bin/env bash

"# Auto-select global QUANTIZATION from embedded per-engine choices\n" \
"# - If both engines are AWQ -> QUANTIZATION=awq\n" \
"# - Else default to fp8; per-engine CHAT_/TOOL_QUANTIZATION stay as set by deploy_models.sh\n"

if [ -z "${QUANTIZATION:-}" ] || [ "${QUANTIZATION}" = "auto" ]; then
  CHAT_IS_AWQ=$([ "${DEPLOY_CHAT}" = "1" ] && [ "${CHAT_QUANTIZATION:-}" = "awq" ] && echo 1 || echo 0)

  if [ "${CHAT_IS_AWQ}" = "1" ]; then
    export QUANTIZATION=awq
  else
    export QUANTIZATION=fp8
    # Normalize per-engine defaults when unset
    if [ "${DEPLOY_CHAT}" = "1" ] && [ -z "${CHAT_QUANTIZATION:-}" ]; then export CHAT_QUANTIZATION=fp8; fi
    if [ "${DEPLOY_TOOL}" = "1" ] && [ -z "${TOOL_QUANTIZATION:-}" ]; then export TOOL_QUANTIZATION=fp8; fi
  fi
fi


