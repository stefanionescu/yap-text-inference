#!/usr/bin/env bash

# Core AWQ operations (selection and quantization helpers)

awq_ensure_cache_dir() {
  mkdir -p "${AWQ_CACHE_DIR}"
}

awq_should_use_prequant() {
  # Sets USE_PREQUANT_AWQ=1 if QUANTIZATION=awq and both (or either) AWQ_* models set
  local use=0
  if [ "${QUANTIZATION:-}" = "awq" ]; then
    if [ -n "${AWQ_CHAT_MODEL:-}" ] || [ -n "${AWQ_TOOL_MODEL:-}" ]; then
      use=1
    fi
  fi
  export USE_PREQUANT_AWQ=${use}
}

awq_quantize_tool_if_needed() {
  local out_dir="${AWQ_CACHE_DIR}/tool_awq"
  if [ -f "${out_dir}/awq_config.json" ] || [ -f "${out_dir}/.awq_ok" ]; then
    log_info "Using existing AWQ tool model at ${out_dir}"
    export TOOL_MODEL="${out_dir}"
    export TOOL_QUANTIZATION=awq
    push_awq_to_hf "${out_dir}" "${HF_AWQ_TOOL_REPO}" "${HF_AWQ_COMMIT_MSG_TOOL}"
    return 0
  fi

  log_info "Quantizing tool model to AWQ: ${TOOL_MODEL} -> ${out_dir}"
  if cd "${ROOT_DIR}" && "${ROOT_DIR}/.venv/bin/python" -m src.awq.quantize --model "${TOOL_MODEL}" --out "${out_dir}"; then
    export TOOL_MODEL="${out_dir}"
    export TOOL_QUANTIZATION=awq
    push_awq_to_hf "${out_dir}" "${HF_AWQ_TOOL_REPO}" "${HF_AWQ_COMMIT_MSG_TOOL}"
  else
    log_warn "AWQ quantization failed for tool model; falling back to auto-detected quant (float)"
    unset TOOL_QUANTIZATION
    if [ "${AWQ_FAIL_HARD:-0}" = "1" ]; then
      log_warn "AWQ_FAIL_HARD=1 set; aborting"
      exit 1
    else
      log_warn "NOTE: Deployment will continue with fallback quantization, not AWQ as requested"
    fi
  fi
}

awq_quantize_chat_if_needed() {
  local out_dir="${AWQ_CACHE_DIR}/chat_awq"
  if [[ "${CHAT_MODEL}" == *GPTQ* ]]; then
    log_warn "AWQ selected but GPTQ chat model provided; refusing."
    exit 1
  fi

  if [ -f "${out_dir}/awq_config.json" ] || [ -f "${out_dir}/.awq_ok" ]; then
    log_info "Using existing AWQ chat model at ${out_dir}"
    export CHAT_MODEL="${out_dir}"
    export CHAT_QUANTIZATION=awq
    push_awq_to_hf "${out_dir}" "${HF_AWQ_CHAT_REPO}" "${HF_AWQ_COMMIT_MSG_CHAT}"
    return 0
  fi

  log_info "Quantizing chat model to AWQ: ${CHAT_MODEL} -> ${out_dir}"
  if cd "${ROOT_DIR}" && "${ROOT_DIR}/.venv/bin/python" -m src.awq.quantize --model "${CHAT_MODEL}" --out "${out_dir}"; then
    export CHAT_MODEL="${out_dir}"
    export CHAT_QUANTIZATION=awq
    push_awq_to_hf "${out_dir}" "${HF_AWQ_CHAT_REPO}" "${HF_AWQ_COMMIT_MSG_CHAT}"
  else
    log_warn "AWQ quantization failed for chat model; falling back to auto-detected quant"
    unset CHAT_QUANTIZATION
    if [ "${AWQ_FAIL_HARD:-0}" = "1" ]; then
      log_warn "AWQ_FAIL_HARD=1 set; aborting"
      exit 1
    else
      log_warn "NOTE: Deployment will continue with fallback quantization, not AWQ as requested"
    fi
  fi
}

awq_handle_tool_prequant_or_quantize() {
  if [ -n "${AWQ_TOOL_MODEL:-}" ]; then
    log_info "Using pre-quantized AWQ tool model: ${AWQ_TOOL_MODEL}"
    export TOOL_MODEL="${AWQ_TOOL_MODEL}"
    export TOOL_QUANTIZATION=awq
  else
    awq_quantize_tool_if_needed
  fi
}

awq_handle_chat_prequant_or_quantize() {
  if [ -n "${AWQ_CHAT_MODEL:-}" ]; then
    log_info "Using pre-quantized AWQ chat model: ${AWQ_CHAT_MODEL}"
    export CHAT_MODEL="${AWQ_CHAT_MODEL}"
    export CHAT_QUANTIZATION=awq
  else
    awq_quantize_chat_if_needed
  fi
}


