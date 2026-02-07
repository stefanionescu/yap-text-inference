"""Engine creation with vLLM V1 compatibility workaround.

vLLM has a bug where AsyncEngineArgs contains scale_dtype and zp_dtype fields
that VllmConfig rejects with 'extra inputs not permitted'. This module patches
VllmConfig.__init__ to filter these out.
"""

from __future__ import annotations

import contextlib
import os
from functools import wraps
from typing import Any

from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine

from src.config import UNSUPPORTED_QUANT_DTYPE_FIELDS


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


@contextlib.contextmanager
def _patched_vllm_config():
    """Temporarily patch VllmConfig to accept scale_dtype/zp_dtype."""
    from vllm.config import VllmConfig  # noqa: PLC0415

    original_init = VllmConfig.__init__

    @wraps(original_init)
    def filtered_init(self: Any, *args: Any, **kwargs: Any) -> None:
        for field in UNSUPPORTED_QUANT_DTYPE_FIELDS:
            kwargs.pop(field, None)
        return original_init(self, *args, **kwargs)

    VllmConfig.__init__ = filtered_init
    try:
        yield
    finally:
        VllmConfig.__init__ = original_init


def create_engine_with_fallback(engine_args: AsyncEngineArgs) -> AsyncLLMEngine:
    """Create an engine with vLLM V1 compatibility fixes."""
    is_local_awq = getattr(engine_args, "_is_local_awq", False)
    offline_ctx = _local_model_offline_context() if is_local_awq else contextlib.nullcontext()

    with offline_ctx, _patched_vllm_config():
        return AsyncLLMEngine.from_engine_args(engine_args)


__all__ = ["create_engine_with_fallback"]
