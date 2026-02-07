"""Factory function for creating classifier adapter instances.

This module provides a function to create a ClassifierToolAdapter instance.
The singleton management is handled by the registry module.
"""

from __future__ import annotations

from src.config import (
    TOOL_COMPILE,
    TOOL_DECISION_THRESHOLD,
    TOOL_GPU_FRAC,
    TOOL_MAX_LENGTH,
    TOOL_MICROBATCH_MAX_DELAY_MS,
    TOOL_MICROBATCH_MAX_SIZE,
    TOOL_MODEL,
)
from src.config.timeouts import TOOL_TIMEOUT_S

from .adapter import ClassifierToolAdapter


def create_classifier_adapter() -> ClassifierToolAdapter:
    """Create a new ClassifierToolAdapter instance using config values.

    This function reads configuration from environment variables and
    creates a fresh adapter instance. It does NOT manage singleton state -
    that's the responsibility of the registry module.

    Returns:
        A new ClassifierToolAdapter instance configured from environment.
    """
    return ClassifierToolAdapter(
        model_path=TOOL_MODEL,
        threshold=TOOL_DECISION_THRESHOLD,
        compile_model=TOOL_COMPILE,
        max_length=TOOL_MAX_LENGTH,
        batch_max_size=TOOL_MICROBATCH_MAX_SIZE,
        batch_max_delay_ms=TOOL_MICROBATCH_MAX_DELAY_MS,
        request_timeout_s=TOOL_TIMEOUT_S,
        gpu_memory_frac=TOOL_GPU_FRAC,
    )


__all__ = ["create_classifier_adapter"]
