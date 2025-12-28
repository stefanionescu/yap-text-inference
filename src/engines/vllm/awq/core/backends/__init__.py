"""Backend-specific quantization routines."""

from .llmcompressor_backend import quantize_with_llmcompressor

__all__ = [
    "quantize_with_llmcompressor",
]
