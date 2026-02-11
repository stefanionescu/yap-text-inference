"""Runtime dependency container.

All long-lived runtime services are assembled at startup and passed explicitly
through request handlers. This avoids lazy singleton initialization during
request processing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from collections.abc import Callable, Awaitable

if TYPE_CHECKING:
    from src.engines.base import BaseEngine
    from src.tokens.tokenizer import FastTokenizer
    from src.engines.vllm.cache import CacheResetManager
    from src.handlers.connections import ConnectionHandler
    from src.handlers.session.manager import SessionHandler
    from src.classifier.adapter import ClassifierToolAdapter


CacheResetFn = Callable[[str, bool], Awaitable[bool]]


@dataclass(slots=True)
class RuntimeDeps:
    """Process-wide runtime services initialized during startup."""

    connections: ConnectionHandler
    session_handler: SessionHandler
    chat_engine: BaseEngine | None
    cache_reset_manager: CacheResetManager | None
    classifier_adapter: ClassifierToolAdapter | None
    chat_tokenizer: FastTokenizer | None
    tool_tokenizer: FastTokenizer | None
    tool_language_detector: Any | None = None

    def supports_cache_reset(self) -> bool:
        return (
            self.chat_engine is not None
            and self.chat_engine.supports_cache_reset
            and self.cache_reset_manager is not None
        )

    async def reset_engine_caches(self, reason: str, *, force: bool = False) -> bool:
        if not self.supports_cache_reset() or self.chat_engine is None or self.cache_reset_manager is None:
            return False
        return await self.cache_reset_manager.try_reset(
            self.chat_engine,
            reason,
            force=force,
        )

    async def clear_caches_on_disconnect(self) -> None:
        if self.supports_cache_reset():
            await self.reset_engine_caches("all_clients_disconnected", force=True)

    def ensure_cache_reset_daemon(self) -> None:
        if not self.supports_cache_reset() or self.cache_reset_manager is None:
            return
        self.cache_reset_manager.ensure_daemon_running(
            lambda reason, force: self.reset_engine_caches(reason, force=force),
        )

    async def shutdown(self) -> None:
        if self.chat_engine is not None:
            await self.chat_engine.shutdown()
