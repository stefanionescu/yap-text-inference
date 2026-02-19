"""Centralized custom exception definitions for the inference server."""

from .limits import RateLimitError
from .validation import ValidationError
from .stream import StreamCancelledError
from .quantization import EngineLabelError
from .shutdown_error import EngineShutdownError
from .not_ready_error import EngineNotReadyError

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
