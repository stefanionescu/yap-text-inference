"""Helpers for CLI/engine scripts.

Submodules:
    awq: AWQ model metadata utilities (read source model from metadata files)
    env_check: Environment probes (torch CUDA version, flashinfer availability)
    filters: Log filtering and noise suppression (HuggingFace, Transformers, TRT)
    model_validate: Early model validation before deployment
    patches: Monkey-patches for transformers compatibility
    quantization: Quantization CLI utilities (model download, checkpoint handling)
    torch_guard: PyTorch/TorchVision CUDA mismatch detection
    trt/: TensorRT-LLM specific utilities (detection, validation)

Note: Filter constants (HF_DOWNLOAD_GROUPS, TRTLLM_NOISE_PATTERNS, etc.) are
now in src/config/filters.py, not in this package.
"""
