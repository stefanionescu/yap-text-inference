#!/usr/bin/env bash
# =============================================================================
# Restart Error Messaging Helpers
# =============================================================================

restart_err_prequant_push_quant() {
  local source_model="${1:-unknown}"
  log_err "[restart] ✗ Cannot use --push-quant with a prequantized model."
  log_err "[restart]   Model '${source_model}' is already quantized."
  log_err "[restart]   There are no local quantization artifacts to upload."
  log_blank
  log_err "[restart]   Options:"
  log_err "[restart]     1. Remove --push-quant to use the prequantized model directly"
  log_err "[restart]     2. Use a base (non-quantized) model if you want to quantize and push"
}

restart_err_no_awq_sources() {
  local deploy_mode="${1:-both}"
  log_err "[restart] ✗ No AWQ models found for deploy mode '${deploy_mode}'"
  log_blank
  log_err "[restart] Options:"
  log_err "[restart]   1. Run full deployment first: bash scripts/main.sh 4bit <chat_model> <tool_model>"
  log_err "[restart]   2. Ensure cached AWQ exports exist in ${ROOT_DIR}/.awq/"
}

restart_err_missing_trt_engine() {
  local deploy_mode="${1:-both}"
  local trt_engine_dir="${TRT_ENGINE_DIR:-<empty>}"

  log_err "[restart] ✗ TRT engine directory not found or not set."
  log_err "[restart]   TRT_ENGINE_DIR='${trt_engine_dir}'"
  log_blank
  log_err "[restart]   TensorRT-LLM requires a pre-built engine. Options:"
  log_err "[restart]     1. Build TRT engine first: bash scripts/quantization/trt_quantizer.sh <model>"
  log_err "[restart]     2. Use vLLM instead: bash scripts/restart.sh --vllm ${deploy_mode}"
  log_err "[restart]     3. Or run full deployment: bash scripts/main.sh --trt <deploy_mode> <model>"
}

