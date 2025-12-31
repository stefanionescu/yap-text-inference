"""Factory for creating classifier adapter instances.

This module provides a thread-safe singleton factory for the classifier adapter.
The adapter is lazily initialized on first access using configuration from
environment variables.
"""

from __future__ import annotations

import threading

from .adapter import ClassifierToolAdapter

# Thread-safe singleton
_lock = threading.Lock()
_instance: ClassifierToolAdapter | None = None


def get_classifier_adapter() -> ClassifierToolAdapter:
    """Get the global classifier adapter instance (thread-safe singleton).
    
    Lazily initializes the classifier using config values from environment
    on first access. Subsequent calls return the same instance.
    
    Thread Safety:
        Uses double-checked locking pattern to ensure thread-safe initialization.
    """
    global _instance
    
    if _instance is None:
        with _lock:
            # Double-check pattern: another thread may have initialized while we waited
            if _instance is None:
                from src.config import (
                    TOOL_MODEL,
                    TOOL_GPU_FRAC,
                    TOOL_DECISION_THRESHOLD,
                    TOOL_COMPILE,
                    TOOL_MAX_LENGTH,
                    TOOL_MICROBATCH_MAX_SIZE,
                    TOOL_MICROBATCH_MAX_DELAY_MS,
                )
                from src.config.timeouts import TOOL_TIMEOUT_S
                
                _instance = ClassifierToolAdapter(
                    model_path=TOOL_MODEL,
                    threshold=TOOL_DECISION_THRESHOLD,
                    compile_model=TOOL_COMPILE,
                    max_length=TOOL_MAX_LENGTH,
                    batch_max_size=TOOL_MICROBATCH_MAX_SIZE,
                    batch_max_delay_ms=TOOL_MICROBATCH_MAX_DELAY_MS,
                    request_timeout_s=TOOL_TIMEOUT_S,
                    gpu_memory_frac=TOOL_GPU_FRAC,
                )
    
    return _instance


def reset_classifier_adapter() -> None:
    """Reset the global classifier adapter instance (for testing).
    
    This clears the singleton, allowing a fresh instance to be created
    on the next call to get_classifier_adapter().
    """
    global _instance
    with _lock:
        _instance = None


__all__ = [
    "get_classifier_adapter",
    "reset_classifier_adapter",
]

