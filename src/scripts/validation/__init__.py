"""Runtime validation utilities for shell script integration.

These modules provide Python validation logic that can be called from shell scripts
via `python -m src.scripts.validation.<module>` or imported directly.

Modules:
    python: Validate Python shared library is loadable
    cuda: Validate CUDA runtime and get driver version
    hf: Validate HuggingFace authentication
    package: Check whether a Python package is importable
"""

from .hf import validate_hf_auth
from .package import is_package_available
from .python import get_python_version, validate_python_library
from .cuda import validate_cuda_runtime, get_cuda_driver_version

__all__ = [
    "get_cuda_driver_version",
    "get_python_version",
    "is_package_available",
    "validate_cuda_runtime",
    "validate_hf_auth",
    "validate_python_library",
]
