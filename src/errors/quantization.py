"""Quantization and engine label exceptions.

This module provides exceptions related to TRT-LLM quantization
and engine label generation.
"""


class EngineLabelError(Exception):
    """Raised when engine label cannot be determined.

    This typically occurs when required environment variables
    (GPU_SM_ARCH, TRT_VERSION, CUDA_VERSION) are not set and
    cannot be auto-detected.
    """


__all__ = ["EngineLabelError"]
