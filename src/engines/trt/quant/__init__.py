"""TRT-LLM quantization metadata and HuggingFace integration."""

from .core.metadata import collect_metadata, detect_base_model, get_engine_label
from .hf.hf_push import push_trt_to_hf
from .utils.detection import (
    detect_cuda_version,
    detect_gpu_name,
    detect_tensorrt_llm_version,
    get_compute_capability_info,
)

__all__ = [
    # Core
    "collect_metadata",
    "detect_base_model",
    "get_engine_label",
    # HF push
    "push_trt_to_hf",
    # Utils
    "detect_cuda_version",
    "detect_gpu_name",
    "detect_tensorrt_llm_version",
    "get_compute_capability_info",
]

