"""Abstract base class for inference engines.

Provides a unified interface for both vLLM and TensorRT-LLM engines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from collections.abc import AsyncGenerator

if TYPE_CHECKING:
    pass


@dataclass(slots=True)
class EngineOutput:
    """Unified output format for streaming generation."""
    
    text: str  # Cumulative generated text
    token_ids: list[int] | None = None  # Token IDs (if available)
    finished: bool = False  # Whether generation is complete
    
    @classmethod
    def from_vllm(cls, output: Any) -> "EngineOutput":
        """Convert vLLM output to unified format."""
        if not getattr(output, "outputs", None):
            return cls(text="", finished=False)
        out = output.outputs[0]
        return cls(
            text=out.text if hasattr(out, "text") else "",
            token_ids=list(out.token_ids) if hasattr(out, "token_ids") else None,
            finished=out.finished if hasattr(out, "finished") else False,
        )
    
    @classmethod
    def from_trt(cls, chunk: Any, prev_text: str = "") -> "EngineOutput":
        """Convert TRT-LLM output to unified format."""
        if not getattr(chunk, "outputs", None):
            return cls(text=prev_text, finished=False)
        out = chunk.outputs[0]
        # TRT can provide .text or token_ids depending on configuration
        text = getattr(out, "text", None) or prev_text
        token_ids = getattr(out, "token_ids", None) or getattr(out, "output_token_ids", None)
        finished = getattr(out, "finished", False)
        return cls(
            text=text,
            token_ids=list(token_ids) if token_ids else None,
            finished=finished,
        )


class BaseEngine(ABC):
    """Abstract base class for inference engines."""
    
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        sampling_params: Any,
        request_id: str,
        *,
        priority: int = 0,
    ) -> AsyncGenerator[EngineOutput, None]:
        """Stream generation outputs.
        
        Args:
            prompt: The input prompt text.
            sampling_params: Engine-specific sampling parameters.
            request_id: Unique identifier for this request.
            priority: Request priority (higher = more urgent).
            
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


class EngineNotReadyError(Exception):
    """Raised when the engine is not ready to serve requests."""
    pass


class EngineShutdownError(Exception):
    """Raised when operations are attempted on a shutdown engine."""
    pass


__all__ = [
    "BaseEngine",
    "EngineOutput",
    "EngineNotReadyError",
    "EngineShutdownError",
]

