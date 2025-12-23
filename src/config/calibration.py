"""Quantization calibration constants.

Functions have been moved to src/helpers/calibration.py.
"""

from __future__ import annotations

import os

from .limits import CHAT_MAX_LEN, CHAT_MAX_OUT


# ------------------------- Dataset defaults ------------------------- #

# Default calibration dataset for quantization
CALIB_DEFAULT_DATASET = os.getenv("CALIB_DATASET_DEFAULT", "open_platypus")

__all__ = [
    "CALIB_DEFAULT_DATASET",
    "CHAT_MAX_LEN",
    "CHAT_MAX_OUT",
]

