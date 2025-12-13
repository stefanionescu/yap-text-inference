"""Engine args builder and related utilities for vLLM engines."""

from __future__ import annotations

import importlib.util
import os

from vllm.engine.arg_utils import AsyncEngineArgs

from src.config.model_profiles import (
    get_tokenizer_kwargs,
    model_needs_memory_optimization,
    model_requires_bfloat16,
    model_requires_fla_runtime,
)
from src.config.env import CHAT_QUANTIZATION, KV_DTYPE, QUANTIZATION
from src.utils.env import env_flag
from src.config.models import _is_local_model_path
from .memory_tuning import (
    auto_max_num_seqs,
    configure_kv_cache,
    get_max_num_seqs_override,
    scale_batching_limits,
)
from .quantization import (
    detect_quantization_backend,
    log_detected_quantization,
    resolve_model_origin,
)
from .tokenizer import inject_tokenizer_kwargs

__all__ = ["make_engine_args"]


def _ensure_fla_runtime_available(model_identifier: str) -> None:
    """Raise a helpful error if fla-core is missing when required."""
    has_fla = importlib.util.find_spec("fla") is not None
    if has_fla:
        return
    raise RuntimeError(
        f"The model '{model_identifier}' requires the flash-linear-attention runtime.\n"
        "Install fla-core>=0.4.0 (included in requirements.txt) before launching the server."
    )


def make_engine_args(model: str, gpu_frac: float, max_len: int) -> AsyncEngineArgs:
    # Prefill chunk sizing (smaller chunk => better TTFB under burst; tune as needed)
    max_batched = int(os.getenv("MAX_NUM_BATCHED_TOKENS_CHAT", "256"))

    # Normalize/validate KV cache dtype
    kv_dtype_value = (KV_DTYPE or "").strip()  # empty => let vLLM decide

    # Select quantization for the chat engine
    selected_quant = (CHAT_QUANTIZATION or QUANTIZATION)

    raw_quant = selected_quant
    inference_quant = raw_quant
    if raw_quant == "awq":
        inference_quant = "awq_marlin"
        detected_quant, quant_payload = detect_quantization_backend(model)
        if detected_quant:
            inference_quant = detected_quant
            log_detected_quantization(model, detected_quant, quant_payload)
    elif raw_quant == "int8":
        # INT8 W8A8 quantization - native on A100 (Ampere) and newer
        inference_quant = "int8"
        print(f"[config] Using INT8 (W8A8) weight quantization for {model}")

    model_origin = resolve_model_origin(model)
    needs_bfloat16 = model_requires_bfloat16(model_origin)
    needs_memory_opt = model_needs_memory_optimization(model_origin)
    needs_mla = model_requires_fla_runtime(model_origin)  # MLA = Multi-Head Latent Attention
    if needs_mla:
        _ensure_fla_runtime_available(model_origin)
        # MLA models don't work with XFORMERS or FLASHINFER backends
        # Unset the backend to let vLLM auto-select the appropriate backend for MLA
        # vLLM will automatically use FLASH_ATTN when MLA is detected
        if os.getenv("VLLM_ATTENTION_BACKEND"):
            os.environ.pop("VLLM_ATTENTION_BACKEND", None)

    dtype_value = "auto"
    # Models that require bfloat16 (e.g., Gemma3) must use it even when quantized
    # For other quantized models, prefer fp16 (Marlin performs better with fp16 on SM < 9.0)
    if needs_bfloat16:
        dtype_value = "bfloat16"
    elif inference_quant in {"awq", "awq_marlin", "compressed-tensors"}:
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

    # Apply model-specific tokenizer kwargs if supported by vLLM
    tok_kwargs = get_tokenizer_kwargs(model_origin)
    inject_tokenizer_kwargs(kwargs, tok_kwargs, model_origin)

    # Memory optimization for models prone to OOM (e.g., Gemma)
    if needs_memory_opt and gpu_frac > 0.85:
        # Slightly reduce GPU memory utilization if not already lowered
        kwargs["gpu_memory_utilization"] = min(gpu_frac, 0.85)

    # Resolve max_num_seqs dynamically to avoid warmup OOMs
    max_num_seqs = get_max_num_seqs_override()
    if max_num_seqs is None:
        max_num_seqs = auto_max_num_seqs(
            gpu_frac=kwargs["gpu_memory_utilization"],
            needs_memory_opt=needs_memory_opt,
        )
    kwargs["max_num_seqs"] = max_num_seqs

    # Special handling for local AWQ models to avoid Hugging Face repo ID validation
    if raw_quant == "awq" and _is_local_model_path(model):
        # For local AWQ models, ensure the path is absolute so vLLM treats it as local
        kwargs["model"] = os.path.abspath(model)

    use_v1 = env_flag("VLLM_USE_V1", True)
    configure_kv_cache(kwargs, kv_dtype_value, use_v1)

    scaled_tokens, scaled_max_seqs = scale_batching_limits(
        max_tokens=kwargs["max_num_batched_tokens"],
        max_seqs=kwargs.get("max_num_seqs"),
        gpu_frac=kwargs["gpu_memory_utilization"],
        engine_role="chat",
    )
    kwargs["max_num_batched_tokens"] = scaled_tokens
    if scaled_max_seqs is not None:
        kwargs["max_num_seqs"] = scaled_max_seqs

    engine_args = AsyncEngineArgs(**kwargs)

    # Add flag for local AWQ handling in engine creation
    if raw_quant == "awq" and _is_local_model_path(model):
        engine_args._is_local_awq = True

    return engine_args
