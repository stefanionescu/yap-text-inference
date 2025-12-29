#!/usr/bin/env bash
# =============================================================================
# vLLM AWQ Quantization Operations
# =============================================================================
# Core AWQ quantization logic for vLLM deployments.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../../lib/common/model_detect.sh"
source "${SCRIPT_DIR}/../../lib/common/awq.sh"
source "${SCRIPT_DIR}/../../lib/deps/venv.sh"

# Ensure AWQ cache directory exists
vllm_awq_ensure_cache_dir() {
  mkdir -p "${AWQ_CACHE_DIR}"
}

# Check if model should use pre-quantized weights
vllm_awq_should_use_prequant() {
  local need_chat="${AWQ_TARGET_CHAT:-0}"
  local use=0 chat_use=0

  if [ "${need_chat}" = "1" ] && model_detect_is_prequant_awq "${CHAT_MODEL:-}"; then
    chat_use=1
    use=1
  fi

  export USE_PREQUANT_AWQ=${use}
  export USE_PREQUANT_AWQ_CHAT=${chat_use}
}

# Quantize chat model to AWQ if needed
vllm_awq_quantize_chat_if_needed() {
  local out_dir="${AWQ_CACHE_DIR}/chat_awq"
  
  if [[ "${CHAT_MODEL}" == *GPTQ* ]]; then
    log_warn "[quant] ⚠ AWQ selected but GPTQ chat model provided; refusing."
    exit 1
  fi

  # Check for existing quantized model
  if awq_chat_cache_ready "${out_dir}"; then
    log_info "[quant] Using existing AWQ chat model..."
    export CHAT_MODEL="${out_dir}"
    export CHAT_QUANTIZATION=awq
    vllm_awq_push_to_hf "${out_dir}"
    return 0
  fi

  log_info "[quant] Quantizing chat model to AWQ..."
  local python_bin
  python_bin="$(get_quant_venv_python)"
  if [ ! -x "${python_bin}" ]; then
    log_err "[quant] ✗ Quantization virtualenv missing (${python_bin}); run --install-deps to set up AWQ deps"
    return 1
  fi
  if cd "${ROOT_DIR}" && "${python_bin}" -m src.engines.vllm.awq.quantize --model "${CHAT_MODEL}" --out "${out_dir}"; then
    export CHAT_MODEL="${out_dir}"
    export CHAT_QUANTIZATION=awq
    vllm_awq_push_to_hf "${out_dir}"
    return 0
  fi

  return 1
}

# Handle pre-quantized or quantize as needed
vllm_awq_handle_chat_prequant_or_quantize() {
  if [ "${USE_PREQUANT_AWQ_CHAT:-0}" = "1" ]; then
    log_info "[quant] Detected pre-quantized AWQ chat model"
    export CHAT_QUANTIZATION=awq
    return 0
  fi
  vllm_awq_quantize_chat_if_needed
}
