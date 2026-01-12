"""Inference engine selection and quantization settings.

This module configures which inference backend to use and how models
are quantized. The two supported engines are:

vLLM:
    - Dynamic batching with PagedAttention
    - Supports AWQ, GPTQ, FP8 quantization
    - Prefix caching for repeated prompts

TensorRT-LLM:
    - Pre-compiled optimized engines
    - Lower latency, higher throughput
    - Built-in KV cache block reuse

Quantization is auto-detected from CHAT_MODEL name:
    - Model name contains 'awq' → 4-bit AWQ
    - Model name contains 'gptq' → 4-bit GPTQ
    - Model name contains 'fp8' → 8-bit FP8

If auto-detection fails, set CHAT_QUANTIZATION manually.

Environment Variables:
    INFERENCE_ENGINE: 'vllm' or 'trt' (default: 'trt')
    CHAT_QUANTIZATION: Override auto-detected quantization (optional)

Note:
    FP8 KV cache setup for vLLM V1 is handled by configure_vllm_fp8_kv_cache()
    in src/helpers/env.py, called during engine initialization.
"""

from __future__ import annotations

import os

from ..helpers.quantization import normalize_engine, detect_chat_quantization


# ============================================================================
# Engine Selection
# ============================================================================

INFERENCE_ENGINE = normalize_engine(os.getenv("INFERENCE_ENGINE", "trt"))


# ============================================================================
# Quantization Configuration
# ============================================================================
# Auto-detected from CHAT_MODEL name. Manual override via CHAT_QUANTIZATION.

_manual_quant = os.getenv("CHAT_QUANTIZATION")
CHAT_QUANTIZATION = _manual_quant or detect_chat_quantization(
    os.getenv("CHAT_MODEL"),
    INFERENCE_ENGINE,
)


# ============================================================================
# Engine Args Defaults
# ============================================================================
# Default values for vLLM engine configuration that can be overridden.

# Default max batched tokens for chunked prefill (used when no profile or env override)
DEFAULT_MAX_BATCHED_TOKENS = int(os.getenv("DEFAULT_MAX_BATCHED_TOKENS", "256"))

# Quantization config file candidates (checked in order)
QUANT_CONFIG_FILENAMES = (
    "config.json",
    "quantization_config.json",
    "quant_config.json",
    "awq_config.json",
)

# AWQ metadata filename written by our quantizer
AWQ_METADATA_FILENAME = "awq_metadata.json"

# Fields in quantization configs that vLLM V1 doesn't support
UNSUPPORTED_QUANT_DTYPE_FIELDS = ("scale_dtype", "zp_dtype")


__all__ = [
    "INFERENCE_ENGINE",
    "CHAT_QUANTIZATION",
    "DEFAULT_MAX_BATCHED_TOKENS",
    "QUANT_CONFIG_FILENAMES",
    "AWQ_METADATA_FILENAME",
    "UNSUPPORTED_QUANT_DTYPE_FIELDS",
]

