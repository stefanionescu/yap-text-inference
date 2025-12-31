"""Model quantization utilities.

This package provides:
- vLLM AWQ quantization (vllm/)
- TRT-LLM quantization metadata (trt/)
"""

from .vllm.core import AWQQuantizer, CalibrationConfig

__all__ = ["AWQQuantizer", "CalibrationConfig"]

