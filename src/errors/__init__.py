"""Centralized custom exception definitions for the inference server."""

from .limits import RateLimitError
from .validation import ValidationError
from .stream import StreamCancelledError
from .shutdown import EngineShutdownError
from .not_ready import EngineNotReadyError
from .quantization import EngineLabelError

__all__ = [
    # Engine errors
    "EngineNotReadyError",
    "EngineShutdownError",
    # Rate limiting
    "RateLimitError",
    # Streaming
    "StreamCancelledError",
    # Validation
    "ValidationError",
    # Quantization
    "EngineLabelError",
]
