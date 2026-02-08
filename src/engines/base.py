"""Abstract base class for inference engines.

This module defines the common interface for all inference backends:

BaseEngine:
    Abstract base class that both VLLMEngine and TRTEngine implement.
    Provides:
    - generate_stream(): Async streaming text generation
    - abort(): Cancel in-flight requests
    - shutdown(): Clean engine termination
    - reset_caches(): Clear prefix caches (vLLM only)

EngineOutput:
    Unified dataclass for streaming outputs, with factory methods
    to convert from engine-specific formats (vLLM or TRT-LLM).

Exceptions:
    EngineNotReadyError: Raised during warmup before engine is ready
    EngineShutdownError: Raised after engine has been shut down

The abstraction allows the rest of the application to work with either
backend without engine-specific code paths.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from collections.abc import AsyncGenerator

from src.state import EngineOutput
from src.errors import EngineNotReadyError, EngineShutdownError


class BaseEngine(ABC):
    """Abstract base class for inference engines.

    This ABC defines the contract that all engine implementations must follow.
    Both VLLMEngine and TRTEngine implement this interface, allowing the
    application to use either backend interchangeably.

    Implementations handle:
    - Engine initialization and model loading
    - Streaming text generation with sampling
    - Request cancellation/abortion
    - Clean shutdown and resource release
    """

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        sampling_params: Any,
        request_id: str,
    ) -> AsyncGenerator[EngineOutput, None]:
        """Stream generation outputs.

        Args:
            prompt: The input prompt text.
            sampling_params: Engine-specific sampling parameters.
            request_id: Unique identifier for this request.

        Yields:
            EngineOutput instances with cumulative text and optional token IDs.
        """
        yield  # type: ignore[misc]  # Abstract generator

    @abstractmethod
    async def abort(self, request_id: str) -> None:
        """Abort an in-flight generation request.

        Args:
            request_id: The request ID to abort.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the engine and release resources."""
        pass

    @property
    def supports_cache_reset(self) -> bool:
        """Whether this engine supports cache reset operations.

        vLLM: True (prefix/mm cache reset)
        TRT-LLM: False (uses block reuse instead)
        """
        return False

    async def reset_caches(self, reason: str) -> bool:
        """Reset engine caches if supported.

        Args:
            reason: Human-readable reason for the reset.

        Returns:
            True if caches were reset, False if not supported or failed.
        """
        return False


__all__ = [
    "BaseEngine",
    "EngineOutput",
    "EngineNotReadyError",
    "EngineShutdownError",
]
