"""Helpers for CLI/engine scripts.

Submodules:
    filters: Log filtering and noise suppression (HuggingFace, Transformers, TRT)
    patches: Monkey-patches for transformers compatibility
    quantization: Quantization CLI utilities (model download, checkpoint handling)

Note: Filter constants (HF_DOWNLOAD_GROUPS, TRTLLM_NOISE_PATTERNS, etc.) are
now in src/config/filters.py, not in this package.
"""
