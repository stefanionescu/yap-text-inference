"""File system utilities for AWQ quantization."""

import os


def file_exists(path: str) -> bool:
    """Check if a file exists safely."""
    try:
        return os.path.exists(path)
    except Exception:
        return False


def is_awq_dir(path: str) -> bool:
    """Check if a directory contains AWQ quantized model files."""
    # Heuristics: common files saved by AutoAWQ
    candidates = [
        os.path.join(path, "awq_config.json"),
        os.path.join(path, "quant_config.json"),
        os.path.join(path, "model.safetensors"),
    ]
    for cand in candidates:
        if file_exists(cand):
            return True
    return False
