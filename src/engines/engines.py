"""Engine management for vLLM chat and tool models."""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass

# Ensure V1 engine path before importing vLLM
os.environ.setdefault("VLLM_USE_V1", "1")
# Use 'spawn' for multiprocessing to avoid CUDA re-initialization issues in forked subprocesses
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

from vllm.engine.async_llm_engine import AsyncLLMEngine

from src.config import (
    CACHE_RESET_INTERVAL_SECONDS,
    CHAT_GPU_FRAC,
    CHAT_MAX_LEN,
    CHAT_MODEL,
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    DEPLOY_DUAL,
    TOOL_GPU_FRAC,
    TOOL_MAX_LEN,
    TOOL_MODEL,
    is_classifier_model,
)
from src.engines.awq_support import create_engine_with_awq_handling
from src.engines.engine_args import make_engine_args

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EngineRoleConfig:
    role: str
    enabled: bool
    model: str
    gpu_frac: float
    max_len: int
    is_chat: bool


class EngineRegistry:
    """Stateful registry that owns lifecycle of chat/tool engines."""

    def __init__(self, configs: list[EngineRoleConfig], cache_reset_interval: int) -> None:
        self._configs = {cfg.role: cfg for cfg in configs}
        self._engines: dict[str, AsyncLLMEngine | None] = {cfg.role: None for cfg in configs}
        self._construction_lock = asyncio.Lock()
        self._cache_reset_lock = asyncio.Lock()
        self._cache_reset_event = asyncio.Event()
        self._cache_reset_interval = cache_reset_interval
        self._last_cache_reset = time.monotonic()

    async def get_engine(self, role: str) -> AsyncLLMEngine:
        cfg = self._configs.get(role)
        if cfg is None:
            raise RuntimeError(f"unknown engine role '{role}'")
        if not cfg.enabled:
            raise RuntimeError(f"{role} engine requested but disabled via configuration")

        await self._initialize_missing_engines()
        engine = self._engines.get(role)
        if engine is None:
            raise RuntimeError(f"{role} engine is unavailable after initialization")
        return engine

    async def _initialize_missing_engines(self) -> None:
        async with self._construction_lock:
            missing = [
                cfg for cfg in self._configs.values() if cfg.enabled and self._engines[cfg.role] is None
            ]
            if not missing:
                return
            for cfg in missing:
                logger.info("building %s engine (model=%s)", cfg.role, cfg.model)
                engine_args = make_engine_args(cfg.model, cfg.gpu_frac, cfg.max_len, cfg.is_chat)
                engine = create_engine_with_awq_handling(engine_args)
                self._engines[cfg.role] = engine
                logger.info("%s engine ready", cfg.role)

    async def reset_caches(self, reason: str, *, force: bool = False) -> bool:
        """Reset prefix/MM caches if interval has elapsed or force is specified."""

        engines = [(role, eng) for role, eng in self._engines.items() if eng is not None]
        if not engines:
            return False

        interval = self._cache_reset_interval
        now = time.monotonic()
        if not force and interval > 0 and (now - self._last_cache_reset) < interval:
            return False

        async with self._cache_reset_lock:
            now = time.monotonic()
            if not force and interval > 0 and (now - self._last_cache_reset) < interval:
                return False

            logger.info("resetting vLLM caches (reason=%s)", reason)
            for name, engine in engines:
                try:
                    await _clean_engine_caches(engine)
                except Exception:  # noqa: BLE001 - best effort
                    logger.warning("cache reset failed for %s engine", name, exc_info=True)

            self._last_cache_reset = now
            self._cache_reset_event.set()
        return True

    def seconds_since_last_cache_reset(self) -> float:
        return max(0.0, time.monotonic() - self._last_cache_reset)

    def cache_reset_reschedule_event(self) -> asyncio.Event:
        return self._cache_reset_event

    async def shutdown(self) -> None:
        for name, engine in list(self._engines.items()):
            if engine is None:
                continue
            try:
                await engine.shutdown()
                logger.info("%s engine shutdown complete", name)
            except Exception:  # noqa: BLE001
                logger.warning("failed to shutdown %s engine", name, exc_info=True)
            finally:
                self._engines[name] = None

    async def clear_all_caches_on_disconnect(self) -> None:
        await self.reset_caches("all_clients_disconnected", force=True)


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


_ENGINE_CONFIGS: list[EngineRoleConfig] = [
    EngineRoleConfig(
        role="chat",
        enabled=DEPLOY_CHAT,
        model=CHAT_MODEL,
        gpu_frac=CHAT_GPU_FRAC,
        max_len=CHAT_MAX_LEN,
        is_chat=True,
    ),
]

# Only add tool engine config for autoregressive LLMs, not classifiers
# Classifier models use transformers directly, not vLLM
_TOOL_IS_CLASSIFIER = is_classifier_model(TOOL_MODEL)

if DEPLOY_TOOL and not DEPLOY_DUAL and not _TOOL_IS_CLASSIFIER:
    _ENGINE_CONFIGS.append(
        EngineRoleConfig(
            role="tool",
            enabled=True,
            model=TOOL_MODEL,
            gpu_frac=TOOL_GPU_FRAC,
            max_len=TOOL_MAX_LEN,
            is_chat=False,
        )
    )

if _TOOL_IS_CLASSIFIER:
    logger.info("Tool model is a classifier (%s), skipping vLLM engine", TOOL_MODEL)

_ENGINE_REGISTRY = EngineRegistry(
    configs=_ENGINE_CONFIGS,
    cache_reset_interval=CACHE_RESET_INTERVAL_SECONDS,
)


async def get_chat_engine() -> AsyncLLMEngine:
    return await _ENGINE_REGISTRY.get_engine("chat")


async def get_tool_engine() -> AsyncLLMEngine:
    """Get the tool engine (vLLM).
    
    Raises RuntimeError if tool model is a classifier (use get_classifier_adapter instead).
    """
    if _TOOL_IS_CLASSIFIER:
        raise RuntimeError(
            f"Tool model '{TOOL_MODEL}' is a classifier. "
            "Use get_classifier_adapter() instead of get_tool_engine()."
        )
    if DEPLOY_DUAL:
        return await get_chat_engine()
    return await _ENGINE_REGISTRY.get_engine("tool")


async def reset_engine_caches(reason: str, *, force: bool = False) -> bool:
    return await _ENGINE_REGISTRY.reset_caches(reason, force=force)


def seconds_since_last_cache_reset() -> float:
    return _ENGINE_REGISTRY.seconds_since_last_cache_reset()


def cache_reset_reschedule_event() -> asyncio.Event:
    return _ENGINE_REGISTRY.cache_reset_reschedule_event()


async def shutdown_engines() -> None:
    await _ENGINE_REGISTRY.shutdown()


async def clear_all_engine_caches_on_disconnect() -> None:
    await _ENGINE_REGISTRY.clear_all_caches_on_disconnect()
