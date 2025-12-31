"""TRT-LLM HuggingFace integration for quantized models."""

from .metadata import collect_metadata, detect_base_model, get_engine_label
from .hf.hf_push import push_trt_to_hf, push_engine_to_hf
from .detection import (
    detect_cuda_version,
    detect_gpu_name,
    detect_tensorrt_llm_version,
    get_compute_capability_info,
)

__all__ = [
    # Metadata
    "collect_metadata",
    "detect_base_model",
    "get_engine_label",
    # HF push
    "push_trt_to_hf",
    "push_engine_to_hf",
    # Utils
    "detect_cuda_version",
    "detect_gpu_name",
    "detect_tensorrt_llm_version",
    "get_compute_capability_info",
]
