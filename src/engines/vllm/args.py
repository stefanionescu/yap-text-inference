"""Engine args builder for vLLM engines.

This module constructs AsyncEngineArgs with all optimizations and
model-specific configurations applied. It handles:

1. Quantization Detection:
   - AWQ, GPTQ, FP8, compressed-tensors
   - Automatic backend selection (awq_marlin, etc.)
   
2. Model Profile Handling:
   - bfloat16 requirements (Kimi, DeepSeek)
   - Memory optimization for OOM-prone models
   - FLA runtime requirements (Kimi)
   - MLA attention (DeepSeek)
   
3. Memory/Batching Tuning:
   - Dynamic max_num_seqs based on GPU memory fraction
   - KV cache dtype configuration
   - Batched tokens scaling
   
4. Tokenizer Configuration:
   - Model-specific tokenizer kwargs
   - Trust remote code for custom implementations

The built AsyncEngineArgs is passed to AsyncLLMEngine.from_engine_args().
"""

from __future__ import annotations

import importlib.util
import os

from vllm.config import AttentionConfig
from vllm.engine.arg_utils import AsyncEngineArgs

from src.helpers.model_profiles import (
    get_max_batched_tokens,
    get_tokenizer_kwargs,
    model_needs_memory_optimization,
    model_requires_bfloat16,
    model_requires_fla_runtime,
    model_uses_mla,
)
from src.config import CHAT_QUANTIZATION, KV_DTYPE, QUANTIZATION
from src.helpers.env import env_flag
from src.helpers.models import is_local_model_path
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
    """Build vLLM AsyncEngineArgs with all optimizations applied.
    
    This function configures the engine with:
    - Chunked prefill for better TTFB
    - Prefix caching enabled
    - Dynamic quantization detection
    - Model-specific dtype/memory settings
    - Automatic max_num_seqs tuning
    
    Args:
        model: Model identifier (HuggingFace ID or local path).
        gpu_frac: GPU memory utilization fraction (0.0-1.0).
        max_len: Maximum model context length.
        
    Returns:
        Configured AsyncEngineArgs ready for engine creation.
    """
    # Capture any explicit backend overrides before we touch vLLM (avoids
    # deprecation warnings when AttentionConfig inspects env vars).
    attention_backend = os.environ.get("VLLM_ATTENTION_BACKEND")
    if attention_backend:
        attention_backend = attention_backend.strip()
        os.environ.pop("VLLM_ATTENTION_BACKEND", None)
    # Normalize/validate KV cache dtype
    kv_dtype_value = (KV_DTYPE or "").strip()

    # Select quantization for the chat engine
    selected_quant = CHAT_QUANTIZATION or QUANTIZATION

    raw_quant = selected_quant
    inference_quant = raw_quant
    if raw_quant == "awq":
        inference_quant = "awq_marlin"
        detected_quant, quant_payload = detect_quantization_backend(model)
        if detected_quant:
            inference_quant = detected_quant
            log_detected_quantization(model, detected_quant, quant_payload)

    model_origin = resolve_model_origin(model)

    # Prefill chunk sizing: check profile first, then env var, then default.
    # Some models (e.g., Mistral 3.2) need higher values for acceptable TTFB.
    env_batched = os.getenv("MAX_NUM_BATCHED_TOKENS_CHAT")
    profile_batched = get_max_batched_tokens(model_origin)
    if env_batched:
        # Explicit env var takes precedence
        max_batched = int(env_batched)
    elif profile_batched is not None:
        # Use profile-specific value
        max_batched = profile_batched
    else:
        # Default fallback
        max_batched = 256
    needs_bfloat16 = model_requires_bfloat16(model_origin)
    needs_memory_opt = model_needs_memory_optimization(model_origin)
    needs_fla = model_requires_fla_runtime(model_origin)
    uses_mla = model_uses_mla(model_origin)

    # FLA models (Kimi) need the fla-core package
    if needs_fla:
        _ensure_fla_runtime_available(model_origin)

    # MLA and FLA models don't work with XFORMERS or FLASHINFER backends
    if uses_mla or needs_fla:
        attention_backend = None

    dtype_value = "auto"
    if needs_bfloat16:
        dtype_value = "bfloat16"
    elif inference_quant in {"awq", "awq_marlin", "compressed-tensors", "fp8"}:
        dtype_value = "float16"

    kwargs = dict(
        model=model,
        trust_remote_code=True,
        tensor_parallel_size=1,
        max_model_len=max_len,
        gpu_memory_utilization=gpu_frac,
        enforce_eager=False,
        enable_chunked_prefill=True,
        max_num_batched_tokens=max_batched,
        enable_prefix_caching=True,
        quantization=inference_quant,
        dtype=dtype_value,
        limit_mm_per_prompt={"image": 0},
    )

    # Apply model-specific tokenizer kwargs if supported by vLLM
    tok_kwargs = get_tokenizer_kwargs(model_origin)
    inject_tokenizer_kwargs(kwargs, tok_kwargs, model_origin)

    # Memory optimization for models prone to OOM
    if needs_memory_opt and gpu_frac > 0.85:
        kwargs["gpu_memory_utilization"] = min(gpu_frac, 0.85)

    # Resolve max_num_seqs dynamically
    max_num_seqs = get_max_num_seqs_override()
    if max_num_seqs is None:
        max_num_seqs = auto_max_num_seqs(
            gpu_frac=kwargs["gpu_memory_utilization"],
            needs_memory_opt=needs_memory_opt,
        )
    kwargs["max_num_seqs"] = max_num_seqs

    # Special handling for local AWQ models
    if raw_quant == "awq" and is_local_model_path(model):
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

    if attention_backend:
        kwargs["attention_config"] = AttentionConfig(backend=attention_backend)

    engine_args = AsyncEngineArgs(**kwargs)

    # Add flag for local AWQ handling in engine creation
    if raw_quant == "awq" and is_local_model_path(model):
        engine_args._is_local_awq = True

    return engine_args
