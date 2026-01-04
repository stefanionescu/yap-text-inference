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
"""

from __future__ import annotations

import os

from ..helpers.env import env_flag
from ..helpers.quantization import (
    normalize_engine,
    classify_prequantized_model,
    classify_trt_prequantized_model,
)
from .gpu import KV_DTYPE


# ============================================================================
# Engine Selection
# ============================================================================

INFERENCE_ENGINE = normalize_engine(os.getenv("INFERENCE_ENGINE", "trt"))


# ============================================================================
# Quantization Configuration
# ============================================================================
# Auto-detected from CHAT_MODEL name. Manual override via CHAT_QUANTIZATION.

def _detect_quantization_from_model() -> str | None:
    """Auto-detect quantization from CHAT_MODEL name."""
    chat_model = os.getenv("CHAT_MODEL")
    if not chat_model:
        return None
    
    # Try TRT-specific detection first (handles trt-awq, trt-fp8, etc.)
    if INFERENCE_ENGINE == "trt":
        trt_quant = classify_trt_prequantized_model(chat_model)
        if trt_quant:
            if trt_quant == "trt_awq":
                return "awq"
            if trt_quant == "trt_fp8":
                return "fp8"
            if trt_quant in ("trt_int8", "trt_8bit"):
                return "int8"
    
    # Fall back to generic pre-quantized detection (awq, gptq)
    return classify_prequantized_model(chat_model)


# Manual override takes precedence, then auto-detection
_manual_quant = os.getenv("CHAT_QUANTIZATION")
CHAT_QUANTIZATION = _manual_quant or _detect_quantization_from_model()

# ============================================================================
# vLLM V1 FP8 KV Cache Setup
# ============================================================================
# V1 engine requires explicit environment variable for FP8 KV cache.
# This is set automatically when KV_DTYPE=fp8.

if env_flag("VLLM_USE_V1", True):
    kv_lower = (KV_DTYPE or "").strip().lower()
    if kv_lower.startswith("fp8"):
        os.environ.setdefault("VLLM_FP8_KV_CACHE_ENABLE", "1")


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

