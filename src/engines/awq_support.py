"""Helpers for AWQ-specific engine initialization."""

from __future__ import annotations

import contextlib
import os

from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine

__all__ = ["create_engine_with_awq_handling"]


@contextlib.contextmanager
def _awq_offline_mode():
    """Temporarily force offline flags for local AWQ model loading."""
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


def create_engine_with_awq_handling(engine_args: AsyncEngineArgs) -> AsyncLLMEngine:
    """Create an engine honoring AWQ offline requirements."""
    is_local_awq = getattr(engine_args, "_is_local_awq", False)

    if is_local_awq:
        if hasattr(engine_args, "_is_local_awq"):
            delattr(engine_args, "_is_local_awq")
        with _awq_offline_mode():
            return AsyncLLMEngine.from_engine_args(engine_args)

    return AsyncLLMEngine.from_engine_args(engine_args)
