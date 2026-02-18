#!/usr/bin/env bash
# =============================================================================
# Quantization Script Configuration Values
# =============================================================================
# Canonical vLLM quantization defaults shared across shell scripts.

# shellcheck disable=SC2034
readonly CFG_QUANT_MODE_8BIT_PLACEHOLDER="8bit"
readonly CFG_QUANT_MODE_8BIT_BACKEND="fp8"
readonly CFG_QUANT_MODE_4BIT_BACKEND="awq"
readonly CFG_QUANT_MODE_GPTQ_BACKEND="gptq_marlin"

# shellcheck disable=SC2034
readonly CFG_QUANT_KV_DTYPE_FP8="fp8"
readonly CFG_QUANT_KV_DTYPE_INT8="int8"
readonly CFG_QUANT_KV_DTYPE_AUTO="auto"
readonly CFG_QUANT_TORCH_ARCH_H100="9.0"
readonly CFG_QUANT_TORCH_ARCH_ADA="8.9"
readonly CFG_QUANT_TORCH_ARCH_A100="8.0"
readonly CFG_QUANT_ENFORCE_EAGER_DEFAULT="0"
readonly CFG_QUANT_MAX_BATCHED_TOKENS_CHAT="256"
readonly CFG_QUANT_MAX_BATCHED_TOKENS_TOOL="224"
readonly CFG_QUANT_TOOL_TIMEOUT_S="10"
readonly CFG_QUANT_GEN_TIMEOUT_S="60"
readonly CFG_QUANT_PREBUFFER_MAX_CHARS_HOPPER="256"
readonly CFG_QUANT_PREBUFFER_MAX_CHARS_A100="1000"
readonly CFG_QUANT_PYTORCH_ALLOC_CONF="expandable_segments:True"
readonly CFG_QUANT_CUDA_DEVICE_MAX_CONNECTIONS="1"

# shellcheck disable=SC2034
readonly CFG_QUANT_BACKEND_FLASHINFER="FLASHINFER"
readonly CFG_QUANT_BACKEND_XFORMERS="XFORMERS"
readonly CFG_HF_CA_CERTS_PATH="/etc/ssl/certs/ca-certificates.crt"
readonly CFG_HF_HUB_DISABLE_TELEMETRY="1"
readonly CFG_HF_HUB_ENABLE_HF_TRANSFER_DEFAULT="0"
