"""TRT-LLM AWQ utilities."""

from .detection import (
    detect_cuda_version,
    detect_gpu_name,
    detect_tensorrt_llm_version,
    get_compute_capability_info,
)

__all__ = [
    "detect_cuda_version",
    "detect_gpu_name",
    "detect_tensorrt_llm_version",
    "get_compute_capability_info",
]

