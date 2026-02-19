"""Quantization calibration constants."""

from __future__ import annotations

import os

# Default calibration dataset for quantization
CALIB_DEFAULT_DATASET = os.getenv("CALIB_DATASET_DEFAULT", "open_platypus")

__all__ = [
    "CALIB_DEFAULT_DATASET",
]
