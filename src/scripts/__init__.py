"""Helpers for CLI/engine scripts.

Submodules:
    awq: AWQ model metadata utilities (read source model from metadata files)
    env: Environment probes (torch CUDA version, flashinfer availability)
    filters: Log filtering and noise suppression (HuggingFace, Transformers, TRT)
    validate: Early model validation before deployment
    patches: Monkey-patches for transformers compatibility
    quantization: Quantization CLI utilities (model download, checkpoint handling)
    guard: PyTorch/TorchVision CUDA mismatch detection
    trt/: TensorRT-LLM specific utilities (detection, validation)

Note: Filter constants (HF_DOWNLOAD_GROUPS, TRTLLM_NOISE_PATTERNS, etc.) are
in the filters config module, not in this package.
"""
