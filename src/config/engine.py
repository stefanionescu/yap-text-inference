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

Quantization is auto-detected in two stages:
    1. Model name heuristics (e.g. 'awq', 'gptq', 'fp8' in CHAT_MODEL)
    2. Config file inspection (reads quant_method from config.json on disk)

The second stage covers local paths like /opt/models/chat where the
directory name carries no quantization markers.

If auto-detection still fails, set CHAT_QUANTIZATION manually.

Environment Variables:
    INFERENCE_ENGINE: 'vllm' or 'trt' (used when DEPLOY_MODE includes chat)
        Tool-only deployments set INFERENCE_ENGINE to None.
    CHAT_QUANTIZATION: Override auto-detected quantization (optional)

Note:
    FP8 KV cache setup for vLLM V1 is handled by the env helpers module
    during engine initialization.
"""

from __future__ import annotations

import os

from .deploy import DEPLOY_CHAT
from ..helpers.quantization import normalize_engine, detect_chat_quantization

# ============================================================================
# Engine Selection
# ============================================================================

if DEPLOY_CHAT:
    INFERENCE_ENGINE: str | None = normalize_engine(os.getenv("INFERENCE_ENGINE", "trt"))
else:
    # Tool-only deployments do not use chat inference engines.
    INFERENCE_ENGINE = None


# ============================================================================
# Quantization Configuration
# ============================================================================
# Auto-detected from CHAT_MODEL name or config files. Manual override via CHAT_QUANTIZATION.

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

# AWQ metadata filename written by our quantizer
AWQ_METADATA_FILENAME = "awq_metadata.json"

# Fields stripped from quantization configs when preparing vLLM engine args
UNSUPPORTED_QUANT_DTYPE_FIELDS = ("scale_dtype", "zp_dtype")

__all__ = [
    "INFERENCE_ENGINE",
    "CHAT_QUANTIZATION",
    "DEFAULT_MAX_BATCHED_TOKENS",
    "AWQ_METADATA_FILENAME",
    "UNSUPPORTED_QUANT_DTYPE_FIELDS",
]
