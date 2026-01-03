"""Centralized exception classes for the inference server.

This module re-exports all domain-specific exceptions from their respective
modules, providing a single import point for error handling.

Organization:
    - engine.py: Engine lifecycle errors (not ready, shutdown)
    - rate_limit.py: Rate limiting errors with retry info
    - stream.py: Streaming/cancellation errors
    - validation.py: Input validation errors with error codes
    - quantization.py: Quantization/engine label errors
"""

from .engine import EngineNotReadyError, EngineShutdownError
from .rate_limit import RateLimitError
from .stream import StreamCancelledError
from .validation import ValidationError
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

