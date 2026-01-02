"""Engine creation fallback helpers for handling legacy configs.

This module provides helpers for:
1. Local AWQ model loading (forcing offline mode)
2. Stripping unsupported quantization dtype fields from engine args
"""

from __future__ import annotations

import contextlib
import logging
import os
from typing import Any

from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine

from src.config import UNSUPPORTED_QUANT_DTYPE_FIELDS

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _local_model_offline_context():
    """Temporarily force offline flags for local model loading.
    
    This prevents HuggingFace Hub from trying to fetch remote files
    when loading a local AWQ-quantized model.
    """
    original_offline = os.environ.get("HF_HUB_OFFLINE")
    original_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        yield
    finally:
        if original_offline is not None:
            os.environ["HF_HUB_OFFLINE"] = original_offline
        else:
            os.environ.pop("HF_HUB_OFFLINE", None)
        if original_transformers_offline is not None:
            os.environ["TRANSFORMERS_OFFLINE"] = original_transformers_offline
        else:
            os.environ.pop("TRANSFORMERS_OFFLINE", None)


def _get_engine_args_field_names(engine_args: AsyncEngineArgs) -> list[str]:
    """Get the field names from engine args (annotations or instance dict)."""
    annotations = getattr(engine_args.__class__, "__annotations__", {}) or {}
    names = list(annotations) or list(getattr(engine_args, "__dict__", {}).keys())
    if "quantization_config" not in names and hasattr(engine_args, "quantization_config"):
        names.append("quantization_config")
    return names


def _strip_unsupported_quant_dtype_fields(engine_args: AsyncEngineArgs) -> AsyncEngineArgs | None:
    """Rebuild engine args without unsupported quant dtype fields.

    vLLM V1 rejects scale_dtype and zp_dtype. Some quantized exports
    still carry these keys, so we strip them and retry engine creation.
    
    Returns None if no fields were removed (nothing to retry).
    """
    source_names = _get_engine_args_field_names(engine_args)
    filtered_kwargs: dict[str, Any] = {}
    removed = False

    for name in source_names:
        if name in UNSUPPORTED_QUANT_DTYPE_FIELDS:
            removed = True
            continue
        if not hasattr(engine_args, name):
            continue

        value = getattr(engine_args, name)
        
        # Clean nested quantization_config dict
        if name == "quantization_config" and isinstance(value, dict):
            cleaned = {k: v for k, v in value.items() if k not in UNSUPPORTED_QUANT_DTYPE_FIELDS}
            if cleaned != value:
                removed = True
            value = cleaned

        filtered_kwargs[name] = value

    if not removed:
        return None

    new_args = AsyncEngineArgs(**filtered_kwargs)
    if hasattr(engine_args, "_is_local_awq"):
        new_args._is_local_awq = engine_args._is_local_awq
    return new_args


def _is_unsupported_quant_dtype_error(error: Exception) -> bool:
    """Check if error is a ValidationError about unsupported quant dtype fields."""
    if error.__class__.__name__ != "ValidationError":
        return False
    message = str(error)
    return bool(message) and any(field in message for field in UNSUPPORTED_QUANT_DTYPE_FIELDS)


def create_engine_with_fallback(engine_args: AsyncEngineArgs) -> AsyncLLMEngine:
    """Create an engine with fallback for unsupported quant dtype fields.
    
    Handles two cases:
    1. Local AWQ models need offline mode to prevent Hub lookups
    2. Legacy quant configs with scale_dtype/zp_dtype need those fields stripped
    """
    def _build(args: AsyncEngineArgs) -> AsyncLLMEngine:
        is_local_awq = getattr(args, "_is_local_awq", False)
        ctx = _local_model_offline_context() if is_local_awq else contextlib.nullcontext()
        with ctx:
            return AsyncLLMEngine.from_engine_args(args)

    try:
        return _build(engine_args)
    except Exception as exc:  # noqa: BLE001
        if not _is_unsupported_quant_dtype_error(exc):
            raise
        fallback_args = _strip_unsupported_quant_dtype_fields(engine_args)
        if fallback_args is None:
            raise
        logger.warning(
            "vLLM: engine args include unsupported quant dtype knobs; retrying without scale/zp dtype fields"
        )
        return _build(fallback_args)


__all__ = ["create_engine_with_fallback"]

