"""AWQ-specific calibration and quantization constants.

Functions have been moved to src/helpers/awq.py.
"""

from __future__ import annotations

import os

from .limits import CHAT_MAX_LEN, CHAT_MAX_OUT


# ------------------------- Dataset defaults ------------------------- #

AWQ_DEFAULT_DATASET = os.getenv("AWQ_CALIB_DATASET_DEFAULT", "open_platypus")

# ----------------------- AWQ markers ------------------------- #

AWQ_MODEL_MARKERS: tuple[str, ...] = (
    "awq",
    "w4a16",
    "nvfp4",
    "compressed-tensors",
    "autoround",
)


__all__ = [
    "AWQ_DEFAULT_DATASET",
    "AWQ_MODEL_MARKERS",
    "CHAT_MAX_LEN",
    "CHAT_MAX_OUT",
]
