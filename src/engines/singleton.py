"""Shared singleton pattern for inference engines.

This module provides a reusable AsyncSingleton class that handles the
thread-safe, async-safe initialization pattern used by both vLLM and TRT engines.

The pattern includes:
- Double-checked locking with asyncio.Lock
- Lazy initialization on first access
- Clean shutdown with lock protection
- Type-safe generic implementation

Usage:
    class MyEngineSingleton(AsyncSingleton[MyEngine]):
        async def _create_instance(self) -> MyEngine:
            # Create and return engine instance
            return MyEngine(...)

        async def _shutdown_instance(self, instance: MyEngine) -> None:
            # Clean up the engine
            await instance.shutdown()

    singleton = MyEngineSingleton()
    engine = await singleton.get()
    await singleton.shutdown()
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class AsyncSingleton(ABC, Generic[T]):
    """Thread-safe, async-safe singleton pattern for engine instances.

    Subclasses must implement _create_instance() and optionally _shutdown_instance().
    """

    def __init__(self) -> None:
        self._instance: T | None = None
        self._lock = asyncio.Lock()

    @abstractmethod
    async def _create_instance(self) -> T:
        """Create the singleton instance. Called once under lock."""
        ...

    async def _shutdown_instance(self, instance: T) -> None:
        """Shutdown the instance. Override for custom cleanup."""
        if hasattr(instance, "shutdown"):
            await instance.shutdown()  # type: ignore[union-attr]

    async def get(self) -> T:
        """Get the singleton instance, creating it if needed.

        Uses double-checked locking for performance:
        - Fast path: return cached instance without lock
        - Slow path: acquire lock and create if still None
        """
        if self._instance is not None:
            return self._instance

        async with self._lock:
            # Double-check after acquiring lock
            if self._instance is not None:
                return self._instance

            self._instance = await self._create_instance()
            return self._instance

    async def shutdown(self) -> None:
        """Shutdown and clear the singleton instance."""
        instance = self._instance
        if instance is None:
            return

        async with self._lock:
            instance = self._instance
            if instance is None:
                return

            await self._shutdown_instance(instance)
            self._instance = None

    @property
    def is_initialized(self) -> bool:
        """Check if the singleton has been initialized."""
        return self._instance is not None


__all__ = ["AsyncSingleton"]
