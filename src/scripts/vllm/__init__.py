"""vLLM Python helpers for shell scripts.

This module provides Python utilities used by vLLM shell scripts.

Submodules:
    detection: CUDA/torch version detection, vLLM installation checks
"""

from src.scripts.vllm.detection import get_cuda_version, get_vllm_version, get_torch_version, is_vllm_installed

__all__ = [
    "get_cuda_version",
    "get_torch_version",
    "get_vllm_version",
    "is_vllm_installed",
]
