#!/usr/bin/env bash

# Core AWQ operations (selection and quantization helpers)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../common/model_detect.sh"

awq_ensure_cache_dir() {
  mkdir -p "${AWQ_CACHE_DIR}"
}

awq_should_use_prequant() {
  local need_chat="${AWQ_TARGET_CHAT:-0}"
  local use=0 chat_use=0

  if [ "${need_chat}" = "1" ] && model_detect_is_prequant_awq "${CHAT_MODEL:-}"; then
    chat_use=1
    use=1
  fi

  export USE_PREQUANT_AWQ=${use}
  export USE_PREQUANT_AWQ_CHAT=${chat_use}
}

awq_quantize_chat_if_needed() {
  local out_dir="${AWQ_CACHE_DIR}/chat_awq"
  if [[ "${CHAT_MODEL}" == *GPTQ* ]]; then
    log_warn "[quant] AWQ selected but GPTQ chat model provided; refusing."
    exit 1
  fi

  if [ -f "${out_dir}/.awq_ok" ] || [ -f "${out_dir}/awq_metadata.json" ] || [ -f "${out_dir}/awq_config.json" ]; then
    log_info "[quant] Using existing AWQ chat model at ${out_dir}"
    export CHAT_MODEL="${out_dir}"
    export CHAT_QUANTIZATION=awq
    push_awq_to_hf "${out_dir}"
    return 0
  fi

  log_info "[quant] Quantizing chat model to AWQ: ${CHAT_MODEL} -> ${out_dir}"
  if cd "${ROOT_DIR}" && "${ROOT_DIR}/.venv/bin/python" -m src.engines.vllm.awq.quantize --model "${CHAT_MODEL}" --out "${out_dir}"; then
    export CHAT_MODEL="${out_dir}"
    export CHAT_QUANTIZATION=awq
    push_awq_to_hf "${out_dir}"
    return 0
  fi

  log_error "[quant] AWQ quantization failed for chat model (${CHAT_MODEL}); aborting deployment."
  return 1
}

awq_handle_chat_prequant_or_quantize() {
  if [ "${USE_PREQUANT_AWQ_CHAT:-0}" = "1" ]; then
    log_info "[quant] Detected pre-quantized AWQ chat model; skipping quantization: ${CHAT_MODEL}"
    export CHAT_QUANTIZATION=awq
    return 0
  fi
  awq_quantize_chat_if_needed
}


