"""TRT-LLM quantization metadata and detection utilities."""

from .detection import detect_cuda_version, detect_gpu_name, detect_tensorrt_llm_version, get_compute_capability_info
from .metadata import collect_metadata, detect_base_model, get_engine_label

__all__ = [
    # Metadata
    "collect_metadata",
    "detect_base_model",
    "get_engine_label",
    # Detection
    "detect_cuda_version",
    "detect_gpu_name",
    "detect_tensorrt_llm_version",
    "get_compute_capability_info",
]
