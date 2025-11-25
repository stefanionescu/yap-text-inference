#!/usr/bin/env bash

# Core AWQ operations (selection and quantization helpers)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../common/model_detect.sh"

awq_ensure_cache_dir() {
  mkdir -p "${AWQ_CACHE_DIR}"
}

awq_should_use_prequant() {
  local need_chat="${AWQ_TARGET_CHAT:-0}"
  local need_tool="${AWQ_TARGET_TOOL:-0}"
  local use=0 chat_use=0 tool_use=0

  if [ "${need_chat}" = "1" ] && model_detect_is_prequant_awq "${CHAT_MODEL:-}"; then
    chat_use=1
    use=1
  fi
  if [ "${need_tool}" = "1" ] && model_detect_is_prequant_awq "${TOOL_MODEL:-}"; then
    tool_use=1
    use=1
  fi

  export USE_PREQUANT_AWQ=${use}
  export USE_PREQUANT_AWQ_CHAT=${chat_use}
  export USE_PREQUANT_AWQ_TOOL=${tool_use}
}

awq_quantize_tool_if_needed() {
  local out_dir="${AWQ_CACHE_DIR}/tool_awq"
  if [ -f "${out_dir}/.awq_ok" ] || [ -f "${out_dir}/awq_metadata.json" ] || [ -f "${out_dir}/awq_config.json" ]; then
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
    return 0
  fi

  log_error "AWQ quantization failed for tool model (${TOOL_MODEL}); aborting deployment."
  return 1
}

awq_quantize_chat_if_needed() {
  local out_dir="${AWQ_CACHE_DIR}/chat_awq"
  if [[ "${CHAT_MODEL}" == *GPTQ* ]]; then
    log_warn "AWQ selected but GPTQ chat model provided; refusing."
    exit 1
  fi

  if [ -f "${out_dir}/.awq_ok" ] || [ -f "${out_dir}/awq_metadata.json" ] || [ -f "${out_dir}/awq_config.json" ]; then
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
    return 0
  fi

  log_error "AWQ quantization failed for chat model (${CHAT_MODEL}); aborting deployment."
  return 1
}

awq_handle_tool_prequant_or_quantize() {
  if [ "${USE_PREQUANT_AWQ_TOOL:-0}" = "1" ]; then
    log_info "Detected pre-quantized AWQ tool model; skipping quantization: ${TOOL_MODEL}"
    export TOOL_QUANTIZATION=awq
    return 0
  fi
  awq_quantize_tool_if_needed
}

awq_handle_chat_prequant_or_quantize() {
  if [ "${USE_PREQUANT_AWQ_CHAT:-0}" = "1" ]; then
    log_info "Detected pre-quantized AWQ chat model; skipping quantization: ${CHAT_MODEL}"
    export CHAT_QUANTIZATION=awq
    return 0
  fi
  awq_quantize_chat_if_needed
}


