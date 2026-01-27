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

from typing import Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from src.errors import EngineNotReadyError, EngineShutdownError


@dataclass(slots=True)
class EngineOutput:
    """Unified output format for streaming generation.
    
    This dataclass provides a common format for generation outputs,
    abstracting away differences between vLLM and TRT-LLM output structures.
    
    Attributes:
        text: Cumulative generated text (grows with each yield).
        token_ids: Optional list of token IDs generated so far.
        finished: True when generation is complete (stop token or max_tokens).
    """
    
    text: str  # Cumulative generated text
    token_ids: list[int] | None = None  # Token IDs (if available)
    finished: bool = False  # Whether generation is complete
    
    @classmethod
    def from_vllm(cls, output: Any) -> EngineOutput:
        """Convert vLLM RequestOutput to unified format.
        
        vLLM outputs have structure:
            output.outputs[0].text -> cumulative text
            output.outputs[0].token_ids -> list of token IDs
            output.outputs[0].finished -> completion flag
        
        Args:
            output: vLLM RequestOutput object.
            
        Returns:
            EngineOutput with extracted fields.
        """
        if not getattr(output, "outputs", None):
            return cls(text="", finished=False)
        out = output.outputs[0]
        return cls(
            text=out.text if hasattr(out, "text") else "",
            token_ids=list(out.token_ids) if hasattr(out, "token_ids") else None,
            finished=out.finished if hasattr(out, "finished") else False,
        )
    
    @classmethod
    def from_trt(cls, chunk: Any, prev_text: str = "") -> EngineOutput:
        """Convert TRT-LLM generation output to unified format.
        
        TRT-LLM output format varies by version but typically includes:
            chunk.outputs[0].text -> generated text (may be incremental)
            chunk.outputs[0].token_ids or output_token_ids -> token IDs
            chunk.outputs[0].finished -> completion flag
        
        Args:
            chunk: TRT-LLM generation chunk.
            prev_text: Previous text for incremental decoding.
            
        Returns:
            EngineOutput with extracted fields.
        """
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
