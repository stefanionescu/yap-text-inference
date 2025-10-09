"""Model-specific adapters for AWQ quantization."""

from .awq_chat_adapter import compute_chat_calibration_seqlen
from .awq_hammer_adapter import (
    apply_hammer_awq_adapters,
    compute_hammer_calibration_seqlen,
    is_hammer_model,
)

__all__ = [
    "compute_chat_calibration_seqlen",
    "apply_hammer_awq_adapters", 
    "compute_hammer_calibration_seqlen",
    "is_hammer_model",
]
