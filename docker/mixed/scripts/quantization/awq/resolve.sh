#!/usr/bin/env bash

# Determine whether user specified pre-quantized AWQ repos
USE_PREQUANT_AWQ=0
if [ -n "${AWQ_CHAT_MODEL:-}" ] || [ -n "${AWQ_TOOL_MODEL:-}" ]; then
  USE_PREQUANT_AWQ=1
  log_info "Using pre-quantized AWQ models from Hugging Face"
fi

# If pre-quantized AWQ provided, assign models accordingly
if [ "${USE_PREQUANT_AWQ}" = "1" ]; then
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    if [ -n "${AWQ_TOOL_MODEL:-}" ]; then
      export TOOL_MODEL="${AWQ_TOOL_MODEL}"; export TOOL_QUANTIZATION=awq
    else
      if OUT=$(quantize_model "tool" "${TOOL_MODEL}" "${TOOL_AWQ_DIR}" "${HF_AWQ_COMMIT_MSG_TOOL:-}" "${HF_AWQ_TOOL_REPO:-}"); then
        export TOOL_MODEL="${OUT}"; export TOOL_QUANTIZATION=awq
      else
        log_warn "AWQ quantization failed for tool model; keeping original"
      fi
    fi
  fi
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    if [ -n "${AWQ_CHAT_MODEL:-}" ]; then
      export CHAT_MODEL="${AWQ_CHAT_MODEL}"; export CHAT_QUANTIZATION=awq
    else
      if [[ "${CHAT_MODEL}" == *GPTQ* ]]; then
        log_warn "AWQ selected but GPTQ chat model provided; refusing."; exit 1
      fi
      if OUT=$(quantize_model "chat" "${CHAT_MODEL}" "${CHAT_AWQ_DIR}" "${HF_AWQ_COMMIT_MSG_CHAT:-}" "${HF_AWQ_CHAT_REPO:-}"); then
        export CHAT_MODEL="${OUT}"; export CHAT_QUANTIZATION=awq
      else
        log_warn "AWQ quantization failed for chat model; keeping original"
      fi
    fi
  fi
else
  # Local quantization for selected engines
  if [ "${DEPLOY_TOOL}" = "1" ]; then
    if OUT=$(quantize_model "tool" "${TOOL_MODEL}" "${TOOL_AWQ_DIR}" "${HF_AWQ_COMMIT_MSG_TOOL:-}" "${HF_AWQ_TOOL_REPO:-}"); then
      export TOOL_MODEL="${OUT}"; export TOOL_QUANTIZATION=awq
    else
      log_warn "AWQ quantization failed for tool model; keeping original"
    fi
  fi
  if [ "${DEPLOY_CHAT}" = "1" ]; then
    if [[ "${CHAT_MODEL}" == *GPTQ* ]]; then
      log_warn "AWQ selected but GPTQ chat model provided; refusing."; exit 1
    fi
    if OUT=$(quantize_model "chat" "${CHAT_MODEL}" "${CHAT_AWQ_DIR}" "${HF_AWQ_COMMIT_MSG_CHAT:-}" "${HF_AWQ_CHAT_REPO:-}"); then
      export CHAT_MODEL="${OUT}"; export CHAT_QUANTIZATION=awq
    else
      log_warn "AWQ quantization failed for chat model; keeping original"
    fi
  fi
fi


