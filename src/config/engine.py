"""Inference engine selection and quantization settings.

This module configures which inference backend to use and how models
are quantized. The two supported engines are:

vLLM (default for development):
    - Dynamic batching with PagedAttention
    - Supports AWQ, GPTQ, FP8 quantization
    - Prefix caching for repeated prompts
    - Requires periodic cache reset

TensorRT-LLM (recommended for production):
    - Pre-compiled optimized engines
    - Lower latency, higher throughput
    - Built-in KV cache block reuse
    - No runtime compilation

Quantization Options:
    - awq: 4-bit AWQ (best quality/size tradeoff)
    - gptq: 4-bit GPTQ 
    - gptq_marlin: GPTQ with Marlin kernels (faster)
    - fp8: 8-bit FP8 (requires Ada/Hopper GPUs)
    - 8bit: Generic 8-bit (maps to fp8 or int8_sq based on GPU)
    - 4bit: Generic 4-bit (maps to awq)

Environment Variables:
    INFERENCE_ENGINE: 'vllm' or 'trt' (default: 'trt')
    QUANTIZATION: Quantization mode (required for LLMs)
    CHAT_QUANTIZATION: Override quantization for chat model only
"""

from __future__ import annotations

import os

from ..helpers.env import env_flag
from ..helpers.quantization import normalize_engine
from .gpu import KV_DTYPE


# ============================================================================
# Engine Selection
# ============================================================================
# Both engines support the same model formats but have different tradeoffs.

INFERENCE_ENGINE = normalize_engine(os.getenv("INFERENCE_ENGINE", "trt"))

# ============================================================================
# Quantization Configuration
# ============================================================================
# Quantization reduces model size and increases throughput at the cost of
# some quality. AWQ 4-bit is recommended for most use cases.

QUANTIZATION = os.getenv("QUANTIZATION")  # Global default
CHAT_QUANTIZATION = os.getenv("CHAT_QUANTIZATION")  # Optional chat-specific override

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
    "QUANTIZATION",
    "CHAT_QUANTIZATION",
    "DEFAULT_MAX_BATCHED_TOKENS",
    "QUANT_CONFIG_FILENAMES",
    "AWQ_METADATA_FILENAME",
    "UNSUPPORTED_QUANT_DTYPE_FIELDS",
]

