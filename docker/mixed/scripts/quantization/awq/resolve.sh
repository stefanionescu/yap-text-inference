#!/usr/bin/env bash

source "${ROOT_DIR}/scripts/lib/common/model_detect.sh"

if [ "${DEPLOY_CHAT}" = "1" ]; then
  if model_detect_is_awq_name "${CHAT_MODEL:-}"; then
    log_info "Detected pre-quantized AWQ chat model; skipping quantization"
    export CHAT_QUANTIZATION=awq
  else
    if [[ "${CHAT_MODEL}" == *GPTQ* ]]; then
      log_warn "AWQ selected but GPTQ chat model provided; refusing."; exit 1
    fi
    if OUT=$(quantize_model "chat" "${CHAT_MODEL}" "${CHAT_AWQ_DIR}" "${HF_AWQ_COMMIT_MSG_CHAT:-}" "${HF_AWQ_CHAT_REPO:-}"); then
      export CHAT_MODEL="${OUT}"; export CHAT_QUANTIZATION=awq
    else
      log_error "AWQ quantization failed for chat model (${CHAT_MODEL}); aborting."
      exit 1
    fi
  fi
fi


