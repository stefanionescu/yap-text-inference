"""Engine warmup utilities for server startup.

This module provides functions to pre-warm inference engines during server
startup, ensuring models are loaded and ready before accepting traffic.
Benefits:
- First request doesn't incur model loading latency
- Configuration errors are caught at startup
- Load balancers can check /healthz after warmup completes

The utilities work with any configured engine (vLLM or TRT-LLM).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

from src.config import INFERENCE_ENGINE

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Engine Warmup
# ============================================================================

async def warm_chat_engine(getter: Callable[[], Awaitable[T]]) -> T:
    """Ensure the chat engine is constructed before serving traffic.

    This pre-warms the inference engine during server startup, which:
    - Loads model weights into GPU memory
    - Compiles CUDA kernels (if using vLLM)
    - Validates the configuration

    Args:
        getter: Async callable that returns the engine instance.

    Returns:
        The warmed engine instance.

    Note:
        For vLLM, this can take 30-60 seconds for large models.
        For TRT-LLM, this loads pre-compiled engines and is faster.
    """
    start = time.perf_counter()
    engine_name = "TRT-LLM" if INFERENCE_ENGINE == "trt" else "vLLM"
    logger.info("preload_engines: warming %s chat engine...", engine_name)
    engine = await getter()
    elapsed = time.perf_counter() - start
    logger.info("preload_engines: %s chat engine ready in %.2fs", engine_name, elapsed)
    return engine


async def warm_classifier() -> None:
    """Ensure the classifier adapter is constructed before serving traffic.

    The classifier is a lightweight PyTorch model used for screenshot
    intent detection. It runs separately from the main chat engine and
    is much faster to load (~5-10 seconds).

    This runs in a thread pool to avoid blocking the event loop during
    model loading.
    """
    from src.classifier import get_classifier_adapter

    start = time.perf_counter()
    logger.info("preload_engines: warming tool classifier adapter...")
    # Run in thread pool - model loading is synchronous and blocking
    await asyncio.to_thread(get_classifier_adapter)
    elapsed = time.perf_counter() - start
    logger.info("preload_engines: tool classifier ready in %.2fs", elapsed)


__all__ = ["warm_chat_engine", "warm_classifier"]

