"""Engine creation with fallback handling for legacy configs.

This module handles:
1. Local AWQ model loading (forces offline mode)
2. Stripping unsupported scale_dtype/zp_dtype fields from vLLM V1
"""

from __future__ import annotations

import contextlib
import logging
import os

from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine

from src.config import UNSUPPORTED_QUANT_DTYPE_FIELDS
from src.quantization.vllm.core.detection import sanitize_quant_metadata

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _local_model_offline_context():
    """Temporarily force offline mode for local model loading."""
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


def _delete_unsupported_attrs(engine_args: AsyncEngineArgs) -> None:
    """Delete unsupported dtype attributes from engine args instance.
    
    vLLM V1's AsyncEngineArgs may have scale_dtype/zp_dtype as class attributes
    with None defaults. VllmConfig rejects these, so we must delete them from
    the instance to prevent them from being passed to create_engine_config().
    """
    for field in UNSUPPORTED_QUANT_DTYPE_FIELDS:
        try:
            delattr(engine_args, field)
        except AttributeError:
            pass  # Field doesn't exist on this instance


def create_engine_with_fallback(engine_args: AsyncEngineArgs) -> AsyncLLMEngine:
    """Create an engine, handling legacy quant configs.
    
    1. Sanitizes model config files (removes scale_dtype/zp_dtype from JSON)
    2. Deletes unsupported attrs from engine_args instance
    3. Uses offline mode for local AWQ models
    """
    # Sanitize config files on disk (local or HF cached)
    model_path = getattr(engine_args, "model", None)
    if model_path:
        sanitize_quant_metadata(model_path)
    
    # Delete unsupported attrs from the engine args instance itself
    _delete_unsupported_attrs(engine_args)
    
    # Use offline mode for local AWQ to prevent Hub lookups
    is_local_awq = getattr(engine_args, "_is_local_awq", False)
    ctx = _local_model_offline_context() if is_local_awq else contextlib.nullcontext()
    
    with ctx:
        return AsyncLLMEngine.from_engine_args(engine_args)


__all__ = ["create_engine_with_fallback"]
