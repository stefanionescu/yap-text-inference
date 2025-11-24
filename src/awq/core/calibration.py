"""Calibration utilities for AWQ quantization."""

from dataclasses import dataclass


@dataclass
class CalibrationConfig:
    """Configuration for AWQ calibration."""
    dataset: str = "open_platypus"
    nsamples: int = 64
    seqlen: int = 2048
    w_bit: int = 4
    q_group_size: int = 128
    zero_point: bool = True
    version: str = "GEMM"
