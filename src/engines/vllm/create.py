"""vLLM engine creation helpers."""

from __future__ import annotations

import os
import contextlib

from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine


@contextlib.contextmanager
def _local_model_offline_context(engine_args: AsyncEngineArgs):
    """Temporarily force offline mode for local AWQ model loading."""
    is_local_awq = getattr(engine_args, "_is_local_awq", False)
    if not is_local_awq:
        yield
        return

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


def create_engine(engine_args: AsyncEngineArgs) -> AsyncLLMEngine:
    """Create a vLLM AsyncLLMEngine from prepared engine args."""
    with _local_model_offline_context(engine_args):
        return AsyncLLMEngine.from_engine_args(engine_args)


__all__ = ["create_engine"]
