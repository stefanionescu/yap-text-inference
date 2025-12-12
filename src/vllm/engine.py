"""Engine management for the single chat vLLM engine."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time

# Ensure V1 engine path before importing vLLM
os.environ.setdefault("VLLM_USE_V1", "1")
# Use 'spawn' for multiprocessing to avoid CUDA re-initialization issues in forked subprocesses
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine

from src.config import (
    CACHE_RESET_INTERVAL_SECONDS,
    CHAT_GPU_FRAC,
    CHAT_MAX_LEN,
    CHAT_MODEL,
    DEPLOY_CHAT,
)
from .args import make_engine_args

logger = logging.getLogger(__name__)

_ENGINE: AsyncLLMEngine | None = None
_ENGINE_LOCK = asyncio.Lock()
_CACHE_RESET_LOCK = asyncio.Lock()
_CACHE_RESET_EVENT = asyncio.Event()
_LAST_CACHE_RESET = time.monotonic()


async def _ensure_engine() -> AsyncLLMEngine:
    if not DEPLOY_CHAT:
        raise RuntimeError("Chat engine requested but DEPLOY_CHAT=0")
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    async with _ENGINE_LOCK:
        if _ENGINE is not None:
            return _ENGINE
        if not CHAT_MODEL:
            raise RuntimeError("CHAT_MODEL is not configured; cannot start chat engine")
        logger.info("vLLM: building chat engine (model=%s)", CHAT_MODEL)
        engine_args = make_engine_args(CHAT_MODEL, CHAT_GPU_FRAC, CHAT_MAX_LEN)
        _ENGINE = _create_engine_with_awq_handling(engine_args)
        logger.info("vLLM: chat engine ready")
        return _ENGINE


async def get_engine() -> AsyncLLMEngine:
    """Return the singleton chat engine instance."""
    return await _ensure_engine()


get_chat_engine = get_engine


async def reset_engine_caches(reason: str, *, force: bool = False) -> bool:
    """Reset prefix/MM caches if interval elapsed (or force)."""
    global _LAST_CACHE_RESET

    engine = _ENGINE
    if engine is None:
        return False

    interval = CACHE_RESET_INTERVAL_SECONDS
    now = time.monotonic()
    if not force and interval > 0 and (now - _LAST_CACHE_RESET) < interval:
        return False

    async with _CACHE_RESET_LOCK:
        now = time.monotonic()
        if not force and interval > 0 and (now - _LAST_CACHE_RESET) < interval:
            return False

        logger.info("resetting vLLM cache (reason=%s)", reason)
        try:
            await _clean_engine_caches(engine)
        except Exception:
            logger.warning("cache reset failed", exc_info=True)
            return False

        _LAST_CACHE_RESET = time.monotonic()
        _CACHE_RESET_EVENT.set()
    return True


def seconds_since_last_cache_reset() -> float:
    return max(0.0, time.monotonic() - _LAST_CACHE_RESET)


def cache_reset_reschedule_event() -> asyncio.Event:
    return _CACHE_RESET_EVENT


async def shutdown_engines() -> None:
    """Shut down the chat engine if it has been initialized."""
    global _ENGINE
    engine = _ENGINE
    if engine is None:
        return

    async with _ENGINE_LOCK:
        engine = _ENGINE
        if engine is None:
            return
        try:
            await engine.shutdown()
            logger.info("vLLM: chat engine shutdown complete")
        except Exception:
            logger.warning("vLLM: chat engine shutdown failed", exc_info=True)
        finally:
            _ENGINE = None


async def clear_all_engine_caches_on_disconnect() -> None:
    await reset_engine_caches("all_clients_disconnected", force=True)


async def _clean_engine_caches(engine: AsyncLLMEngine) -> None:
    """Best-effort clearing of caches using the public vLLM APIs."""
    for method_name in ("reset_mm_cache", "reset_prefix_cache"):
        method = getattr(engine, method_name, None)
        if method is None:
            continue
        try:
            result = method()
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            # Best effort only
            pass


# ---------------------------------------------------------------------------
# AWQ offline mode handling
# ---------------------------------------------------------------------------
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


def _create_engine_with_awq_handling(engine_args: AsyncEngineArgs) -> AsyncLLMEngine:
    """Create an engine honoring AWQ offline requirements."""
    is_local_awq = getattr(engine_args, "_is_local_awq", False)

    if is_local_awq:
        if hasattr(engine_args, "_is_local_awq"):
            delattr(engine_args, "_is_local_awq")
        with _awq_offline_mode():
            return AsyncLLMEngine.from_engine_args(engine_args)

    return AsyncLLMEngine.from_engine_args(engine_args)
