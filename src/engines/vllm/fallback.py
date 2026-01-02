"""Engine creation with vLLM V1 compatibility workaround.

vLLM has a bug where AsyncEngineArgs contains scale_dtype and zp_dtype fields
that VllmConfig rejects with 'extra inputs not permitted'. This module patches
the engine creation to filter these out.
"""

from __future__ import annotations

import contextlib
import logging
import os
from functools import wraps
from typing import Any

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


def _patch_create_engine_config(engine_args: AsyncEngineArgs) -> None:
    """Patch create_engine_config to filter unsupported fields before VllmConfig.
    
    vLLM's AsyncEngineArgs has scale_dtype/zp_dtype as dataclass fields that
    VllmConfig rejects. We wrap create_engine_config to intercept and filter.
    """
    original_method = engine_args.create_engine_config
    
    @wraps(original_method)
    def patched_create_engine_config(*args: Any, **kwargs: Any) -> Any:
        # The issue is inside VllmConfig.__init__ which is called by the original
        # method. We need to patch VllmConfig temporarily.
        from vllm.config import VllmConfig
        
        original_init = VllmConfig.__init__
        
        @wraps(original_init)
        def filtered_init(self: Any, *init_args: Any, **init_kwargs: Any) -> None:
            # Remove the problematic fields before passing to pydantic
            for field in UNSUPPORTED_QUANT_DTYPE_FIELDS:
                init_kwargs.pop(field, None)
            return original_init(self, *init_args, **init_kwargs)
        
        VllmConfig.__init__ = filtered_init
        try:
            return original_method(*args, **kwargs)
        finally:
            VllmConfig.__init__ = original_init
    
    # Replace the method on this specific instance
    engine_args.create_engine_config = patched_create_engine_config


def create_engine_with_fallback(engine_args: AsyncEngineArgs) -> AsyncLLMEngine:
    """Create an engine with vLLM V1 compatibility fixes.
    
    1. Sanitizes model config files (removes scale_dtype/zp_dtype from JSON)
    2. Patches create_engine_config to filter unsupported fields
    3. Uses offline mode for local AWQ models
    """
    # Sanitize config files on disk
    model_path = getattr(engine_args, "model", None)
    if model_path:
        sanitize_quant_metadata(model_path)
    
    # Patch the instance method to filter unsupported fields
    _patch_create_engine_config(engine_args)
    
    # Use offline mode for local AWQ
    is_local_awq = getattr(engine_args, "_is_local_awq", False)
    ctx = _local_model_offline_context() if is_local_awq else contextlib.nullcontext()
    
    with ctx:
        return AsyncLLMEngine.from_engine_args(engine_args)


__all__ = ["create_engine_with_fallback"]
