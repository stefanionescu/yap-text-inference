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
from src.config import (
    CHAT_QUANTIZATION,
    DEFAULT_MAX_BATCHED_TOKENS,
    KV_DTYPE,
    QUANTIZATION,
)
from src.config.limits import MEMORY_OPT_GPU_FRAC_CAP
from src.config.quantization import FLOAT16_QUANT_METHODS
from src.helpers.env import env_flag
from src.helpers.models import is_local_model_path
from .memory_tuning import (
    auto_max_num_seqs,
    configure_kv_cache,
    scale_batching_limits,
)
from src.quantization.vllm.core.detection import (
    detect_quant_backend,
    log_quant_detection,
    resolve_model_origin,
)
from .tokenizer import inject_tokenizer_kwargs


def _ensure_fla_runtime_available(model_identifier: str) -> None:
    """Raise a helpful error if fla-core is missing when required."""
    has_fla = importlib.util.find_spec("fla") is not None
    if has_fla:
        return
    raise RuntimeError(
        f"The model '{model_identifier}' requires the flash-linear-attention runtime.\n"
        "Install fla-core>=0.4.0 (included in requirements.txt) before launching the server."
    )


def _resolve_quantization(model: str, raw_quant: str | None) -> tuple[str | None, dict]:
    """Resolve the quantization backend and detect from model config if needed.
    
    Returns:
        Tuple of (inference_quant, quant_payload) where quant_payload contains
        detected quantization metadata.
    """
    if not raw_quant:
        return None, {}
    
    inference_quant = raw_quant
    quant_payload = {}
    
    if raw_quant == "awq":
        inference_quant = "awq_marlin"
        detected_quant, quant_payload = detect_quant_backend(model)
        if detected_quant:
            inference_quant = detected_quant
            log_quant_detection(model, detected_quant, quant_payload)
    
    return inference_quant, quant_payload


def _resolve_max_batched_tokens(model_origin: str) -> int:
    """Resolve max batched tokens from env, profile, or default."""
    env_batched = os.getenv("MAX_NUM_BATCHED_TOKENS_CHAT")
    if env_batched:
        return int(env_batched)
    
    profile_batched = get_max_batched_tokens(model_origin)
    if profile_batched is not None:
        return profile_batched
    
    return DEFAULT_MAX_BATCHED_TOKENS


def _resolve_dtype(
    needs_bfloat16: bool,
    inference_quant: str | None,
) -> str:
    """Resolve the dtype based on model requirements and quantization."""
    if needs_bfloat16:
        return "bfloat16"
    if inference_quant in FLOAT16_QUANT_METHODS:
        return "float16"
    return "auto"


class _ModelRequirements:
    """Container for model-specific requirements from profile lookup."""
    
    __slots__ = (
        "model_origin",
        "needs_bfloat16",
        "needs_memory_opt",
        "needs_fla",
        "uses_mla",
        "max_batched_tokens",
        "tokenizer_kwargs",
    )
    
    def __init__(self, model: str) -> None:
        self.model_origin = resolve_model_origin(model)
        self.needs_bfloat16 = model_requires_bfloat16(self.model_origin)
        self.needs_memory_opt = model_needs_memory_optimization(self.model_origin)
        self.needs_fla = model_requires_fla_runtime(self.model_origin)
        self.uses_mla = model_uses_mla(self.model_origin)
        self.max_batched_tokens = _resolve_max_batched_tokens(self.model_origin)
        self.tokenizer_kwargs = get_tokenizer_kwargs(self.model_origin)


def _build_base_kwargs(
    model: str,
    gpu_frac: float,
    max_len: int,
    inference_quant: str | None,
    requirements: _ModelRequirements,
) -> dict:
    """Build the base engine kwargs dictionary."""
    dtype_value = _resolve_dtype(requirements.needs_bfloat16, inference_quant)
    
    return dict(
        model=model,
        trust_remote_code=True,
        tensor_parallel_size=1,
        max_model_len=max_len,
        gpu_memory_utilization=gpu_frac,
        enforce_eager=False,
        enable_chunked_prefill=True,
        max_num_batched_tokens=requirements.max_batched_tokens,
        enable_prefix_caching=True,
        quantization=inference_quant,
        dtype=dtype_value,
        limit_mm_per_prompt={"image": 0},
    )


def _apply_memory_tuning(
    kwargs: dict,
    requirements: _ModelRequirements,
) -> None:
    """Apply memory optimization and batch size tuning."""
    gpu_frac = kwargs["gpu_memory_utilization"]
    
    # Memory optimization for models prone to OOM
    if requirements.needs_memory_opt and gpu_frac > MEMORY_OPT_GPU_FRAC_CAP:
        kwargs["gpu_memory_utilization"] = min(gpu_frac, MEMORY_OPT_GPU_FRAC_CAP)
    
    # Resolve max_num_seqs dynamically based on GPU memory
    kwargs["max_num_seqs"] = auto_max_num_seqs(
        gpu_frac=kwargs["gpu_memory_utilization"],
        needs_memory_opt=requirements.needs_memory_opt,
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
    # Capture attention backend before vLLM inspects env vars
    attention_backend = os.environ.pop("VLLM_ATTENTION_BACKEND", None)
    if attention_backend:
        attention_backend = attention_backend.strip() or None
    
    # Normalize KV cache dtype
    kv_dtype_value = (KV_DTYPE or "").strip()

    # Resolve quantization backend
    raw_quant = CHAT_QUANTIZATION or QUANTIZATION
    inference_quant, _ = _resolve_quantization(model, raw_quant)

    # Get model requirements from profile
    requirements = _ModelRequirements(model)

    # FLA models (Kimi) need the fla-core package
    if requirements.needs_fla:
        _ensure_fla_runtime_available(requirements.model_origin)

    # MLA and FLA models don't work with XFORMERS or FLASHINFER backends
    if requirements.uses_mla or requirements.needs_fla:
        attention_backend = None

    # Build base kwargs
    kwargs = _build_base_kwargs(model, gpu_frac, max_len, inference_quant, requirements)

    # Apply tokenizer kwargs if supported by vLLM
    tokenizer_kwargs = requirements.tokenizer_kwargs
    inject_tokenizer_kwargs(kwargs, tokenizer_kwargs, requirements.model_origin)

    # Apply memory tuning
    _apply_memory_tuning(kwargs, requirements)

    # Special handling for local AWQ models
    is_local_awq = raw_quant == "awq" and is_local_model_path(model)
    if is_local_awq:
        kwargs["model"] = os.path.abspath(model)

    # Configure KV cache
    use_v1 = env_flag("VLLM_USE_V1", True)
    configure_kv_cache(kwargs, kv_dtype_value, use_v1)

    # Scale batching limits based on available memory
    scaled_tokens, scaled_max_seqs = scale_batching_limits(
        max_tokens=kwargs["max_num_batched_tokens"],
        max_seqs=kwargs.get("max_num_seqs"),
        gpu_frac=kwargs["gpu_memory_utilization"],
        engine_role="chat",
    )
    kwargs["max_num_batched_tokens"] = scaled_tokens
    if scaled_max_seqs is not None:
        kwargs["max_num_seqs"] = scaled_max_seqs

    # Apply attention backend if specified
    if attention_backend:
        kwargs["attention_config"] = AttentionConfig(backend=attention_backend)

    engine_args = AsyncEngineArgs(**kwargs)

    # Flag for local AWQ handling in engine creation
    if is_local_awq:
        engine_args._is_local_awq = True

    return engine_args


__all__ = ["make_engine_args"]
