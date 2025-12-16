"""Inference engine selection and quantization settings."""

from __future__ import annotations

import os

from ..utils.env import env_flag
from .quantization import normalize_engine
from .gpu import KV_DTYPE


# Engine selection: 'trt' (default) or 'vllm'
INFERENCE_ENGINE = normalize_engine(os.getenv("INFERENCE_ENGINE", "trt"))

# Quantization mode: 'fp8' | 'gptq' | 'gptq_marlin' | 'awq' | '8bit' | '4bit'
QUANTIZATION = os.getenv("QUANTIZATION")
CHAT_QUANTIZATION = os.getenv("CHAT_QUANTIZATION")  # Optional override for chat

# vLLM V1 engine FP8 KV cache enablement
if env_flag("VLLM_USE_V1", True):
    kv_lower = (KV_DTYPE or "").strip().lower()
    if kv_lower.startswith("fp8"):
        os.environ.setdefault("VLLM_FP8_KV_CACHE_ENABLE", "1")


__all__ = [
    "INFERENCE_ENGINE",
    "QUANTIZATION",
    "CHAT_QUANTIZATION",
]

