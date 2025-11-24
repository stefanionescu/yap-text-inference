"""File system utilities for AWQ quantization."""

import os


def file_exists(path: str) -> bool:
    """Check if a file exists safely."""
    try:
        return os.path.exists(path)
    except Exception:
        return False


def is_awq_dir(path: str) -> bool:
    """Check if a directory looks like an AWQ export."""
    candidates = [
        os.path.join(path, ".awq_ok"),
        os.path.join(path, "awq_metadata.json"),
        os.path.join(path, "quantization_config.json"),
        os.path.join(path, "quant_config.json"),
    ]
    return any(file_exists(cand) for cand in candidates)
