"""Model-specific adapters for AWQ quantization."""

from .awq_chat_adapter import compute_chat_calibration_seqlen

__all__ = [
    "compute_chat_calibration_seqlen",
]
