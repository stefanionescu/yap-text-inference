"""TRT-LLM Python helpers for shell scripts.

This module provides Python utilities used by TRT shell scripts, extracting
complex inline Python into testable, maintainable modules.

Submodules:
    detection: Checkpoint format detection, CUDA driver queries, HF engine listing
    validation: Python library, CUDA runtime, MPI, and TRT installation validation
"""

from src.scripts.trt.validation import (
    validate_mpi_runtime,
    validate_cuda_runtime,
    validate_python_libraries,
    validate_trt_installation,
)
from src.scripts.trt.detection import (
    list_remote_engines,
    get_cuda_driver_version,
    detect_checkpoint_qformat,
    read_checkpoint_quant_info,
)

__all__ = [
    "detect_checkpoint_qformat",
    "get_cuda_driver_version",
    "list_remote_engines",
    "read_checkpoint_quant_info",
    "validate_cuda_runtime",
    "validate_mpi_runtime",
    "validate_python_libraries",
    "validate_trt_installation",
]
