"""Centralized exception classes for the inference server.

This module re-exports all domain-specific exceptions from their respective
modules, providing a single import point for error handling.

Organization:
    - engine.py: Engine lifecycle errors (not ready, shutdown)
    - limits.py: Rate limiting errors with retry info
    - stream.py: Streaming/cancellation errors
    - validation.py: Input validation errors with error codes
    - quantization.py: Quantization/engine label errors
    - classify.py: Exception-to-telemetry label mapping
"""

from .limits import RateLimitError
from .classify import classify_error
from .validation import ValidationError
from .stream import StreamCancelledError
from .quantization import EngineLabelError
from .engine import EngineNotReadyError, EngineShutdownError

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
    # Classification
    "classify_error",
]
