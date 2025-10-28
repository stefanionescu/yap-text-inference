"""Model-specific adapters for AWQ quantization."""

from .awq_chat_adapter import compute_chat_calibration_seqlen
from .awq_toolcall_adapter import (
    apply_toolcall_awq_adapters,
    compute_toolcall_calibration_seqlen,
    is_toolcall_model,
)

__all__ = [
    "compute_chat_calibration_seqlen",
    "apply_toolcall_awq_adapters", 
    "compute_toolcall_calibration_seqlen",
    "is_toolcall_model",
]
