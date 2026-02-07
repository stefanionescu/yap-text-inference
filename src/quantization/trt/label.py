"""Engine label generation for TRT-LLM models.

This module handles engine label generation for HuggingFace repo organization.
Engine labels encode the GPU architecture, TRT-LLM version, and CUDA version
to ensure compatibility when downloading pre-built engines.

Engine labels follow the format: {sm_arch}_trt-llm-{version}_cuda{version}
Example: sm90_trt-llm-0.17.0_cuda12.8
"""

from __future__ import annotations

import os
import json
from pathlib import Path

from src.errors import EngineLabelError
from src.state import EnvironmentInfo

# ============================================================================
# Environment Helpers
# ============================================================================

def _env_int(name: str, default: int | None) -> int | None:
    """Get int from env var, handling empty strings."""
    val = os.getenv(name, "")
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    """Get string from env var, handling empty strings."""
    val = os.getenv(name, "")
    return val if val else default


# ============================================================================
# Engine Label
# ============================================================================

def get_engine_label(engine_path: Path) -> str:
    """Generate engine label from build metadata or environment variables.

    Args:
        engine_path: Path to TRT-LLM engine directory.

    Returns:
        Engine label string (e.g., "sm90_trt-llm-0.17.0_cuda12.8").

    Raises:
        EngineLabelError: If required values cannot be determined.
    """
    # Try build_metadata.json first - it has the exact values used at build time
    meta_path = engine_path / "build_metadata.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            sm = meta.get("sm_arch")
            trt_ver = meta.get("tensorrt_llm_version")
            cuda_ver = meta.get("cuda_toolkit") or meta.get("cuda_version")

            if sm and trt_ver and cuda_ver:
                return f"{sm}_trt-llm-{trt_ver}_cuda{cuda_ver}"
        except Exception:
            pass

    # Fall back to environment
    env_info = EnvironmentInfo.from_env()
    return env_info.make_label()


__all__ = [
    "EngineLabelError",
    "get_engine_label",
    "_env_int",
    "_env_str",
]
