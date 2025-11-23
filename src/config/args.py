"""Engine args builder and related utilities for vLLM engines."""

import os
from vllm.engine.arg_utils import AsyncEngineArgs

from .env import (
    KV_DTYPE,
    QUANTIZATION,
    CHAT_QUANTIZATION,
    TOOL_QUANTIZATION,
)
from .quantization import is_lowbit_quantization
from .models import _is_local_model_path


def make_engine_args(model: str, gpu_frac: float, max_len: int, is_chat: bool) -> AsyncEngineArgs:

    # Prefill chunk sizing (smaller chunk => better TTFB under burst; tune as needed)
    max_batched = int(os.getenv(
        "MAX_NUM_BATCHED_TOKENS_CHAT" if is_chat else "MAX_NUM_BATCHED_TOKENS_TOOL",
        "512" if is_chat else "256",
    ))

    # Normalize/validate KV cache dtype
    kv_dtype = (KV_DTYPE or "").strip().lower()  # empty => let vLLM decide

    # Select per-engine quantization:
    # - If CHAT_QUANTIZATION/TOOL_QUANTIZATION is set, prefer that.
    # - Else default: chat uses QUANTIZATION; tool inherits QUANTIZATION for low-bit modes.
    if is_chat:
        selected_quant = (CHAT_QUANTIZATION or QUANTIZATION)
    else:
        if TOOL_QUANTIZATION:
            selected_quant = TOOL_QUANTIZATION
        elif is_lowbit_quantization(QUANTIZATION):
            selected_quant = QUANTIZATION
        else:
            selected_quant = None

    raw_quant = selected_quant
    inference_quant = raw_quant
    if raw_quant == "awq":
        inference_quant = "awq_marlin"

    dtype_value = "auto"
    if inference_quant in {"awq", "awq_marlin"}:
        dtype_value = "float16"

    # Build kwargs for V1 engine.
    kwargs = dict(
        model=model,
        trust_remote_code=True,
        tensor_parallel_size=1,
        max_model_len=max_len,
        gpu_memory_utilization=gpu_frac,
        # Allow CUDA graphs for better performance
        enforce_eager=False,
        enable_chunked_prefill=True,
        max_num_batched_tokens=max_batched,
        # Always enable prefix caching for performance
        enable_prefix_caching=True,
        # Weight quantization (None => float weights)
        quantization=inference_quant,
        dtype=dtype_value,
        # Enable per-request priorities used by generate(..., priority=...)
        scheduling_policy="priority",
    )

    # Special handling for local AWQ models to avoid Hugging Face repo ID validation
    if raw_quant == "awq" and _is_local_model_path(model):
        # For local AWQ models, ensure the path is absolute so vLLM treats it as local
        kwargs["model"] = os.path.abspath(model)

    # Only pass kv_cache_dtype if explicitly set AND V1 is off
    # (V1 rejects --kv-cache-dtype and will throw NotImplementedError)
    use_v1 = (os.getenv("VLLM_USE_V1", "1") == "1")
    if (not use_v1) and kv_dtype:
        kwargs["kv_cache_dtype"] = kv_dtype
        # Add KV scale calculation for FP8 KV cache
        if kv_dtype.startswith("fp8"):
            # Enable dynamic k/v scale calculation for FP8 KV cache
            kwargs["calculate_kv_scales"] = True

    engine_args = AsyncEngineArgs(**kwargs)

    # Add flag for local AWQ handling in engine creation
    if raw_quant == "awq" and _is_local_model_path(model):
        engine_args._is_local_awq = True

    return engine_args


__all__ = ["make_engine_args"]


