"""Calibration utilities for AWQ quantization."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CalibrationConfig:
    """Configuration for AWQ calibration."""
    dataset: str = "pileval"
    nsamples: int = 64
    seqlen: int = 2048
    w_bit: int = 4
    q_group_size: int = 128
    zero_point: bool = True
    version: str = "GEMM"


def prepare_tokenizer_for_calibration(tokenizer: Any, target_seqlen: int) -> None:
    """Prepare tokenizer for calibration with the given sequence length."""
    # Some tokenizers need special preparation for calibration
    # This is a placeholder for any tokenizer-specific setup
    if hasattr(tokenizer, 'model_max_length'):
        # Temporarily adjust max length for calibration
        original_max_length = getattr(tokenizer, '_original_max_length', None)
        if original_max_length is None:
            tokenizer._original_max_length = tokenizer.model_max_length
        tokenizer.model_max_length = target_seqlen
