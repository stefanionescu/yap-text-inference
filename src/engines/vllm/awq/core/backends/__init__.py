"""Backend-specific quantization routines."""

from .autoawq_backend import quantize_with_autoawq
from .llmcompressor_backend import quantize_with_llmcompressor

__all__ = [
    "quantize_with_autoawq",
    "quantize_with_llmcompressor",
]


